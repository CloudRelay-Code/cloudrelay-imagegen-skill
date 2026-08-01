#!/usr/bin/env python3
"""Generate or edit images through CloudRelay."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
import uuid


BASE_URL = "https://cloudrelay.cn"
ENV_NAME = "CLOUDRELAY_IMAGE_API_KEY"
USER_AGENT = "Mozilla/5.0 (compatible; cloudrelay-imagegen-skill/1.0)"
TERMINAL_STATUSES = {"completed", "failed", "canceled"}


class CloudRelayError(RuntimeError):
    """Raised for CloudRelay request and response failures."""


def _configure_console_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def _read_windows_user_environment(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
        return str(value).strip() or None
    except OSError:
        return None


def _api_key() -> str:
    key = (os.environ.get(ENV_NAME) or "").strip()
    if not key:
        key = _read_windows_user_environment(ENV_NAME) or ""
    if not key:
        raise CloudRelayError(
            f"{ENV_NAME} is not configured. Create a CloudRelay API key in the "
            'group named "生图专用", then configure the environment variable.'
        )
    return key


def _parse_json(raw: bytes) -> dict:
    text = raw.decode("utf-8", "replace") if raw else ""
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"error": {"message": text.strip()[:500] or "Empty response"}}
    return value if isinstance(value, dict) else {"data": value}


def _error_message(payload: dict) -> str:
    error = payload.get("error", payload)
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


def _request(
    method: str,
    path: str,
    api_key: str,
    body: dict | None = None,
    timeout: float = 60,
) -> tuple[int, dict]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE_URL + path, data=data, method=method)
    request.add_header("Authorization", "Bearer " + api_key)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, _parse_json(response.read())
    except urllib.error.HTTPError as error:
        return error.code, _parse_json(error.read())
    except urllib.error.URLError as error:
        raise CloudRelayError(f"Network request failed: {error.reason}") from error


def _multipart_body(fields: list[tuple[str, object]]) -> tuple[bytes, str]:
    boundary = "cloudrelay-" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields:
        if isinstance(value, tuple):
            filename, data, content_type = value
            parts.append(
                (
                    f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                    f'Content-Type: {content_type}\r\n\r\n'
                ).encode("utf-8")
                + data
                + b"\r\n"
            )
        else:
            parts.append(
                (
                    f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f'{value}\r\n'
                ).encode("utf-8")
            )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _request_multipart(
    path: str,
    api_key: str,
    fields: list[tuple[str, object]],
    timeout: float = 300,
) -> tuple[int, dict]:
    data, content_type = _multipart_body(fields)
    request = urllib.request.Request(BASE_URL + path, data=data, method="POST")
    request.add_header("Authorization", "Bearer " + api_key)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "application/json")
    request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, _parse_json(response.read())
    except urllib.error.HTTPError as error:
        return error.code, _parse_json(error.read())
    except urllib.error.URLError as error:
        raise CloudRelayError(f"Network request failed: {error.reason}") from error


def _safe_job_id(job_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", job_id).strip("._")
    return safe or "cloudrelay-image"


def _download_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as error:
        raise CloudRelayError(f"Image download failed: {error}") from error


def _image_bytes(image: dict, index: int) -> bytes:
    encoded = image.get("b64_json")
    if encoded:
        try:
            return base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise CloudRelayError(f"Image {index} contains invalid base64 data.") from error
    url = image.get("url")
    if url:
        return _download_url(str(url))
    raise CloudRelayError(f"Image {index} contains neither b64_json nor url.")


def _extension(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


def _submit(args: argparse.Namespace, api_key: str) -> tuple[str, dict]:
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "n": args.count,
        "response_format": args.response_format,
    }
    status, job = _request("POST", "/v1/images/jobs", api_key, payload)
    if status not in (200, 202):
        raise CloudRelayError(f"Submission failed (HTTP {status}): {_error_message(job)}")
    job_id = str(job.get("id") or "").strip()
    if not job_id:
        raise CloudRelayError("Submission response did not include a job ID.")
    print(f"Submitted job={job_id} status={job.get('status', 'unknown')}", flush=True)
    return job_id, job


def _submit_edit(args: argparse.Namespace, api_key: str) -> tuple[str, dict]:
    image_path = args.input_image.expanduser().resolve()
    if not image_path.is_file():
        raise CloudRelayError(f"Input image was not found: {image_path}")

    content_type = "image/png"
    if image_path.suffix.lower() in {".jpg", ".jpeg"}:
        content_type = "image/jpeg"
    elif image_path.suffix.lower() == ".webp":
        content_type = "image/webp"

    fields: list[tuple[str, object]] = [
        ("model", args.model),
        ("prompt", args.prompt),
        ("size", args.size),
        ("quality", args.quality),
        ("n", str(args.count)),
        ("response_format", args.response_format),
        ("image", (image_path.name, image_path.read_bytes(), content_type)),
    ]
    status, response = _request_multipart("/v1/images/edits", api_key, fields)
    if status not in (200, 202):
        raise CloudRelayError(
            f"Edit submission failed (HTTP {status}): {_error_message(response)}"
        )

    job_id = str(response.get("id") or "").strip()
    job_status = str(response.get("status") or "").strip()
    if job_id and job_status:
        print(f"Submitted edit job={job_id} status={job_status}", flush=True)
        return job_id, response

    images = response.get("data")
    if not isinstance(images, list) or not images:
        raise CloudRelayError("Edit response contained neither a job ID nor image data.")
    direct_id = f"edit_{response.get('created') or int(time.time())}_{os.getpid()}"
    completed = {
        "status": "completed",
        "result": {"data": images, "usage": response.get("usage")},
    }
    print(f"Completed synchronous edit={direct_id}", flush=True)
    return direct_id, completed


def _poll(job_id: str, api_key: str, timeout: float) -> dict:
    delay = 2.0
    deadline = time.monotonic() + timeout
    last_job: dict = {}
    while time.monotonic() < deadline:
        time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
        status, job = _request("GET", f"/v1/images/jobs/{job_id}", api_key)
        if status == 200:
            last_job = job
            job_status = str(job.get("status") or "unknown")
            print(f"status={job_status}", flush=True)
            if job_status in TERMINAL_STATUSES:
                return job
        elif status in (401, 403, 404):
            raise CloudRelayError(f"Polling failed (HTTP {status}): {_error_message(job)}")
        else:
            print(
                f"Polling warning (HTTP {status}): {_error_message(job)}; retrying",
                file=sys.stderr,
                flush=True,
            )
        delay = min(delay * 1.5, 10.0)
    last_status = last_job.get("status", "unknown")
    raise CloudRelayError(f"Polling timed out for job {job_id}; last status={last_status}.")


def _save_images(job_id: str, job: dict, output_dir: Path) -> list[Path]:
    if job.get("status") != "completed":
        raise CloudRelayError(
            f"Job {job_id} ended with status={job.get('status', 'unknown')}: "
            f"{_error_message(job)}"
        )
    result = job.get("result") or {}
    images = result.get("data") or []
    if not isinstance(images, list) or not images:
        raise CloudRelayError(f"Completed job {job_id} returned no images.")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_job_id(job_id)
    saved: list[Path] = []
    for index, image in enumerate(images):
        if not isinstance(image, dict):
            raise CloudRelayError(f"Image {index} has an unexpected response shape.")
        data = _image_bytes(image, index)
        if not data:
            raise CloudRelayError(f"Image {index} is empty.")
        path = (output_dir / f"{stem}_{index}{_extension(data)}").resolve()
        path.write_bytes(data)
        saved.append(path)

    print(f"Completed {len(saved)} image(s); usage={result.get('usage')}")
    for path in saved:
        print(f"Saved {path}")
    return saved


def _positive_timeout(value: str) -> float:
    timeout = float(value)
    if timeout <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return timeout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or edit images through the CloudRelay image API."
    )
    parser.add_argument("--prompt", required=True, help="Image-generation prompt.")
    parser.add_argument("--model", default="gpt-image-2", help="Image model name.")
    parser.add_argument(
        "--size",
        choices=("auto", "1024x1024", "1536x1024", "1024x1536"),
        default="1024x1024",
    )
    parser.add_argument(
        "--quality",
        choices=("auto", "low", "medium", "high"),
        default="auto",
    )
    parser.add_argument("--count", type=int, choices=range(1, 5), default=1)
    parser.add_argument(
        "--input-image",
        type=Path,
        help="Use the CloudRelay image-edit endpoint with this reference image.",
    )
    parser.add_argument(
        "--response-format",
        choices=("b64_json", "url"),
        default="b64_json",
    )
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--poll-timeout", type=_positive_timeout, default=300.0)
    return parser


def main() -> int:
    _configure_console_utf8()
    args = build_parser().parse_args()
    try:
        api_key = _api_key()
        if args.input_image:
            job_id, submitted_job = _submit_edit(args, api_key)
        else:
            job_id, submitted_job = _submit(args, api_key)
        if submitted_job.get("status") in TERMINAL_STATUSES:
            completed_job = submitted_job
        else:
            completed_job = _poll(job_id, api_key, args.poll_timeout)
        _save_images(job_id, completed_job, args.output_dir)
    except CloudRelayError as error:
        print(f"CloudRelay error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted while waiting for CloudRelay.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
