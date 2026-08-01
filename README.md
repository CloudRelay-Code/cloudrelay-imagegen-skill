# CloudRelay ImageGen Skill

一个面向 Codex 的图片生成与编辑 Skill。它通过 [CloudRelay](https://cloudrelay.cn) 的异步图片 API 提交任务、轮询结果，并将返回的 base64 数据或图片 URL 保存为本地文件。

## 用途

- 使用 `gpt-image-2` 等 CloudRelay 支持的模型生成图片
- 使用参考图片进行图片编辑
- 支持 `1024x1024`、`1536x1024`、`1024x1536` 和自动尺寸
- 支持一次生成 1 至 4 张图片
- 自动等待异步任务完成并保存 PNG、JPEG、GIF 或 WebP 文件
- 将 API Key 保存在环境变量中，不写入提示词、源码或生成目录

脚本只使用 Python 标准库，并将 API 地址固定为 `https://cloudrelay.cn`。

## 环境要求

- Codex 桌面端或其他支持 Skills 的 Codex 环境
- Git
- Python 3.10 或更高版本
- CloudRelay API Key，Key 的分组必须是 `生图专用`

## 安装

### Windows PowerShell

```powershell
git clone https://github.com/CloudRelay-Code/cloudrelay-imagegen-skill.git
New-Item -ItemType Directory -Path "$env:USERPROFILE\.codex\skills" -Force | Out-Null
Copy-Item ".\cloudrelay-imagegen-skill\cloudrelay-imagegen" `
  "$env:USERPROFILE\.codex\skills\" -Recurse -Force
```

### macOS 或 Linux

```bash
git clone https://github.com/CloudRelay-Code/cloudrelay-imagegen-skill.git
mkdir -p ~/.codex/skills
cp -R ./cloudrelay-imagegen-skill/cloudrelay-imagegen ~/.codex/skills/
```

安装后重启 Codex，使其重新加载 Skills。最终目录应为：

```text
~/.codex/skills/cloudrelay-imagegen/
├── SKILL.md
├── agents/openai.yaml
└── scripts/
    ├── configure_api_key.py
    └── generate_image.py
```

## 配置 API Key

先在 [CloudRelay](https://cloudrelay.cn) 创建 API Key，并确保 Key 的分组名称是 `生图专用`。

Windows 用户可以使用随 Skill 提供的隐藏输入脚本。输入过程不会回显 Key：

```powershell
python "$env:USERPROFILE\.codex\skills\cloudrelay-imagegen\scripts\configure_api_key.py"
```

该脚本会把 Key 保存为当前 Windows 用户的持久环境变量 `CLOUDRELAY_IMAGE_API_KEY`。配置后请重启 Codex。

macOS 或 Linux 用户请在启动 Codex 的环境中设置同名环境变量，例如：

```bash
export CLOUDRELAY_IMAGE_API_KEY="your-api-key"
```

不要把真实 API Key 写入仓库、提示词或命令行参数。

## 使用

在 Codex 中直接调用 Skill：

```text
使用 $cloudrelay-imagegen 生成一张 1536x1024 的电影感雪山日出图片，保存到 generated-images。
```

编辑图片时提供本地参考图：

```text
使用 $cloudrelay-imagegen 编辑这张图片，把背景改成夜晚城市，并保持主体不变。
```

也可以直接运行生成脚本：

```powershell
python "$env:USERPROFILE\.codex\skills\cloudrelay-imagegen\scripts\generate_image.py" `
  --prompt "a cinematic sunrise over snowy mountains" `
  --model "gpt-image-2" `
  --size "1536x1024" `
  --quality "high" `
  --count 1 `
  --output-dir ".\generated-images"
```

查看全部参数：

```powershell
python "$env:USERPROFILE\.codex\skills\cloudrelay-imagegen\scripts\generate_image.py" --help
```

## 安全说明

- 仓库不包含任何 API Key 或生成结果。
- 生成脚本不提供命令行 Key 参数，避免凭据进入 Shell 历史。
- Windows 配置脚本使用隐藏输入，并只写入用户级环境变量。
- 请求目标固定为 CloudRelay 官方域名；使用前请自行确认其服务条款、费用与数据政策。

## 许可证

[MIT License](LICENSE)
