#!/usr/bin/env python3
"""Configure the CloudRelay image API key without exposing it on the command line."""

from __future__ import annotations

import argparse
import ctypes
import getpass
import os
from pathlib import Path
import sys


ENV_NAME = "CLOUDRELAY_IMAGE_API_KEY"


def _configure_console_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def _secret_file() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_root).expanduser() if config_root else Path.home() / ".config"
    return root / "cloudrelay" / "imagegen-api-key"


def _validate_key(key: str) -> str:
    key = key.strip()
    if not key:
        raise ValueError("No API key was provided.")
    if any(character.isspace() for character in key):
        raise ValueError("The API key must not contain whitespace.")
    return key


def _read_key() -> str:
    return _validate_key(getpass.getpass("CloudRelay image API key: "))


def _read_key_from_stdin() -> str:
    """Read a user-provided key without placing it in argv or shell history."""
    return _validate_key(sys.stdin.read())


def _read_windows_user_variable() -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as registry_key:
            value, _ = winreg.QueryValueEx(registry_key, ENV_NAME)
        return str(value).strip() or None
    except OSError:
        return None


def _is_configured() -> bool:
    if (os.environ.get(ENV_NAME) or "").strip():
        return True
    if _read_windows_user_variable():
        return True
    try:
        return bool(_secret_file().read_text(encoding="utf-8").strip())
    except OSError:
        return False


def _persist_windows_user_variable(key: str) -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as registry_key:
        winreg.SetValueEx(registry_key, ENV_NAME, 0, winreg.REG_SZ, key)

    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF,
        0x001A,
        0,
        "Environment",
        0x0002,
        5000,
        None,
    )


def _persist_posix_secret_file(key: str) -> Path:
    path = _secret_file()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(key + "\n")
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    path.chmod(0o600)
    return path


def main() -> int:
    _configure_console_utf8()
    parser = argparse.ArgumentParser(
        description=f"Securely configure {ENV_NAME} for CloudRelay image requests."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether a key is configured without displaying its value.",
    )
    parser.add_argument(
        "--key-stdin",
        action="store_true",
        help="Read the key from stdin; use only when the user has provided it directly.",
    )
    args = parser.parse_args()

    if args.check:
        if _is_configured():
            print("configured")
            return 0
        print("missing")
        return 1

    try:
        key = _read_key_from_stdin() if args.key_stdin else _read_key()
        # Make the credential available immediately to this process as well as
        # to future processes launched after the persistent write completes.
        os.environ[ENV_NAME] = key
        if os.name == "nt":
            _persist_windows_user_variable(key)
            location = f"the Windows user environment variable {ENV_NAME}"
        else:
            path = _persist_posix_secret_file(key)
            location = f"the user-only file {path}"
    except (OSError, ValueError) as error:
        print(f"Configuration failed: {error}", file=sys.stderr)
        return 1

    print(f"Configured {location}.")
    print("The key value was not displayed or written to the skill directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
