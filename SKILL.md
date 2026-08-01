---
name: cloudrelay-imagegen
description: "Generate or edit images through the CloudRelay asynchronous image API, including secure API-key setup, job submission, polling, and saving base64 or URL results. Use when the user asks for CloudRelay image generation or editing, mentions the CloudRelay image API, or explicitly invokes cloudrelay-imagegen."
---

# CloudRelay Image Generation

Use the bundled scripts for every CloudRelay image request. Keep credentials out of conversations, source files, shell history, repositories, and generated artifacts.

## Purpose

CloudRelay provides this asynchronous image workflow because native synchronous image-generation requests can run beyond Cloudflare's approximately 120-second request window and be terminated before the client receives the result. This skill teaches agent clients to submit a job once, retain its job ID, poll with separate requests until a terminal status is reached, and then save the returned images. Preserve that asynchronous flow; never replace polling with one long-running HTTP request or submit a duplicate job merely because generation takes time.

## Workflow

1. Collect the prompt, optional input image, output directory, model, size, quality, and image count. Use these defaults when unspecified:
   - model: `gpt-image-2`
   - size: `1024x1024`
   - quality: `auto`
   - count: `1`
2. Resolve the active skill directory from this `SKILL.md`. Resolve all bundled script paths relative to that directory; do not assume the current working directory is the skill directory.
3. Check credential presence without printing its value:

   ```text
   python "<skill-directory>/scripts/configure_api_key.py" --check
   ```

4. If the key is missing, stop before making an API request. Tell the user to create a key at `https://cloudrelay.cn` whose group is exactly `生图专用`, then ask them to run the following command in their own private terminal:

   ```text
   python "<skill-directory>/scripts/configure_api_key.py"
   ```

   Do not ask the user to paste the key into the conversation. Do not put the key in a command-line argument. The script uses hidden input and stores the credential outside the skill directory. Resume the original request after the user confirms configuration.
5. Choose an output directory inside the current workspace unless the user requests another location. Use a dedicated directory such as `generated-images`; never save outputs inside the skill.
6. Run `scripts/generate_image.py` with explicit, quoted arguments:

   ```text
   python "<skill-directory>/scripts/generate_image.py" \
     --prompt "a cinematic sunrise over snowy mountains" \
     --model "gpt-image-2" \
     --size "1536x1024" \
     --quality "high" \
     --count 1 \
     --output-dir "<workspace>/generated-images"
   ```

   Adapt line continuation syntax to the current shell. For an edit, add `--input-image "<path-to-reference-image>"`.
7. Wait for the process to finish. Do not submit a duplicate job while polling.
8. Verify that every reported output exists and inspect each image before claiming success. Report absolute output paths and render images when the host supports visual output.

## Failure Handling

- For `401` or `403`, report that the configured key was rejected and ask the user to confirm it is active and belongs to the `生图专用` group. Do not switch credentials silently.
- For `429`, report the rate or quota limit. Retry only on user request or when the response provides a reasonable retry time.
- For failed or canceled jobs, report the API error without exposing headers or credentials.
- For polling timeouts, report the job ID. Do not submit a replacement automatically.
- Never claim generation succeeded unless an output file exists and has been inspected.

## Script Reference

`scripts/generate_image.py` uses only the Python standard library and fixes the API origin to `https://cloudrelay.cn`.

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
