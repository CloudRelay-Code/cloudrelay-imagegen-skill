---
name: cloudrelay-imagegen
description: Generate and save images through the CloudRelay asynchronous image API at https://cloudrelay.cn, including API-key setup, job submission, polling, and base64 or URL result handling. Use when Codex is asked to create or generate images specifically through CloudRelay, when the user mentions the CloudRelay image API, or when the user explicitly invokes $cloudrelay-imagegen.
---

# CloudRelay Image Generation

Use the bundled scripts for all CloudRelay image requests. Keep credentials out of prompts, source files, shell history, repositories, and generated artifacts.

## Workflow

1. Collect the requested prompt, optional input image for editing, output directory, model, size, quality, and image count. Use these defaults when the user does not specify them:
   - model: `gpt-image-2`
   - size: `1024x1024`
   - quality: `auto`
   - count: `1`
2. Check whether `CLOUDRELAY_IMAGE_API_KEY` is configured without printing its value. On Windows, check both the current process and the persistent user environment:

   ```powershell
   $configured = -not [string]::IsNullOrWhiteSpace($env:CLOUDRELAY_IMAGE_API_KEY)
   if (-not $configured) {
       $configured = -not [string]::IsNullOrWhiteSpace(
           [Environment]::GetEnvironmentVariable("CLOUDRELAY_IMAGE_API_KEY", "User")
       )
   }
   if ($configured) { "configured" } else { "missing" }
   ```

3. If the key is missing, stop before making any API request. Ask the user to open `https://cloudrelay.cn`, create an API key whose group is exactly `生图专用`, and send the new key to Codex so it can be saved as `CLOUDRELAY_IMAGE_API_KEY`. The four group-name characters are Unicode `U+751F U+56FE U+4E13 U+7528` (Python/JSON escape `\u751f\u56fe\u4e13\u7528`); use those code points if a Windows terminal displays mojibake. Do not repeat mojibake to the user. Do not ask the user to paste the key into a tracked file.
4. After the user supplies the key, do not echo it back or expose it in a command-line argument. Run `scripts/configure_api_key.py` in a PTY and send the key to its hidden prompt. The script uses a no-echo password input, stores the key in the Windows user environment, and prints only a confirmation. Verify presence only, never the value. Resume the original image request after configuration.
5. Choose an output directory inside the user's current workspace unless the user requests another location. Create a dedicated directory such as `generated-images` rather than saving output inside this skill.
6. Run `scripts/generate_image.py` with explicit arguments. Quote prompts and paths. Example:

   ```powershell
   python "<skill-directory>\scripts\generate_image.py" `
     --prompt "a cute red panda sitting on a bamboo branch" `
     --model "gpt-image-2" `
     --size "1024x1024" `
     --quality "auto" `
     --count 1 `
     --output-dir "<workspace>\generated-images"
   ```

   For an edit request, add `--input-image "<path-to-reference-image>"`.

7. Wait for the command to finish. Do not start duplicate jobs while polling. If the process is still running, continue waiting until it completes, fails, or reaches its timeout.
8. Inspect each saved image and report the absolute paths. In a visual-capable client, render the resulting images for the user.

## Failure Handling

- For `401` or `403`, state that the configured CloudRelay key was rejected. Ask the user to confirm that it is active and belongs to the `生图专用` group; do not silently switch to another key.
- For `429`, report the rate or quota limit and preserve the job details. Retry only when the user asks or the response provides a reasonable retry time.
- For a failed or canceled job, report the API error without exposing request headers or credentials.
- For polling timeouts, report the job ID so it can be checked later. Do not submit a replacement automatically.
- Never claim an image was generated unless the output file exists and has been inspected.

## Script Reference

`scripts/generate_image.py` uses only the Python standard library and fixes the API origin to `https://cloudrelay.cn`. It supports:

```text
--prompt TEXT
--model NAME
--size auto|1024x1024|1536x1024|1024x1536
--quality auto|low|medium|high
--count 1..4
--input-image PATH
--response-format b64_json|url
--output-dir PATH
--poll-timeout SECONDS
```

Do not modify the base URL or add a command-line API-key option.
