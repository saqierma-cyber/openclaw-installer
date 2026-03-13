# OpenClaw Installer

一键安装 [OpenClaw](https://github.com/openclaw/openclaw) AI 助手的桌面工具。

用户只需双击运行，输入激活码和 API Key，即可自动完成 Node.js 检测安装、OpenClaw 部署、模型配置、Gateway 启动，全程无需终端操作。

## 功能特性

- **一键安装** — 自动检测/安装 Node.js，部署 OpenClaw，配置 Gateway
- **多品牌支持** — 支持 Anthropic、OpenAI、智谱、Kimi、DeepSeek、通义千问等 20+ 大模型
- **API Key 验证** — 安装前自动验证 Key 有效性和额度
- **激活码系统** — 内置远程验证，支持一码一用、机器绑定
- **国内优化** — 从自有服务器下载安装包，绕过 GitHub 访问限制
- **自动配置** — 模拟官方 `openclaw configure` 向导，直接写入配置文件
- **Gateway 自启** — 安装完成自动启动 Gateway 并打开浏览器

## 项目结构

```
openclaw-installer/
├── installer/                 # 安装器核心代码
│   ├── main.py               # GUI 主程序（tkinter 向导界面）
│   └── core/
│       ├── activator.py      # 激活码验证（联网远程验证）
│       ├── api_validator.py  # API Key 验证（多品牌适配）
│       ├── fingerprint.py    # 机器指纹生成
│       ├── node_installer.py # Node.js 自动安装
│       └── openclaw_installer.py  # OpenClaw 安装、配置、启动
├── assets/
│   ├── icon.ico              # 应用图标
│   └── icon.png
├── config.example.py         # 配置示例
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+
pip install -r requirements.txt
```

### 2. 配置

复制配置示例并填写你的服务器信息：

```bash
cp config.example.py config.py
```

需要修改的位置：

| 文件 | 变量 | 说明 |
|------|------|------|
| `installer/core/activator.py` | `SERVER_URL` | 你的验证服务器地址 |
| `installer/core/activator.py` | `SECRET_KEY` | 与服务端一致的签名密钥 |
| `installer/core/openclaw_installer.py` | `OPENCLAW_TGZ_URL` | OpenClaw 安装包下载地址 |
| `installer/main.py` | `TRAY_EXE_URL` | 托盘管家下载地址 |

### 3. 开发模式运行

```bash
python installer/main.py
```

### 4. 打包成 exe

```bash
# Windows 上执行
pip install pyinstaller

pyinstaller --onefile --windowed --name "OpenClaw-Installer" \
  --icon assets/icon.ico \
  --paths installer \
  --hidden-import core.activator \
  --hidden-import core.api_validator \
  --hidden-import core.fingerprint \
  --hidden-import core.node_installer \
  --hidden-import core.openclaw_installer \
  installer/main.py --noconfirm --clean
```

打包后的 exe 在 `dist/` 目录。

## 验证服务器

安装器需要配合验证服务器使用。服务器负责：

- 激活码验证（一码一用、过期检查）
- 托管 OpenClaw 安装包（绕过国内 GitHub 限制）
- 托管托盘管家 exe

服务器端代码**不包含在本仓库中**。你需要自己搭建一个提供以下 API 的服务：

```
POST /api/v1/activate    — 验证激活码
GET  /static/*.tgz       — 下载 OpenClaw 安装包
GET  /static/*.exe       — 下载托盘管家
```

推荐使用 Python FastAPI + SQLite，最低配置 1 核 1GB 内存即可。

## 支持的大模型

| 品牌 | 默认模型 |
|------|----------|
| Anthropic (Claude) | claude-sonnet-4-5 |
| OpenAI (GPT) | gpt-4o |
| 智谱 (GLM) | glm-4-flash |
| Kimi (Moonshot) | moonshot-v1-8k |
| DeepSeek | deepseek-chat |
| 通义千问 (Qwen) | qwen-turbo |
| MiniMax | abab6.5s-chat |
| Google (Gemini) | gemini-pro |
| Mistral | mistral-large-latest |
| Groq | llama-3.1-70b-versatile |
| Ollama (本地) | llama3 |
| 自定义 | 用户指定 |

## 技术细节

- **GUI**: customtkinter / tkinter
- **打包**: PyInstaller (--onefile)
- **签名验证**: HMAC-SHA256 (payload + timestamp + secret)
- **API 验证策略**: 200/400/403 视为有效，仅 401 视为 Key 无效
- **安装方式**: 从服务器下载预打包 tgz，解压到 npm 全局目录
- **Gateway 启动**: PowerShell Start-Process + 完整路径
- **国内优化**: npm 淘宝镜像 + git 代理配置

## 已知问题

- PyInstaller 打包的 exe 可能被杀毒软件误报（建议购买代码签名证书）
- Python 3.14 与 PyInstaller 不兼容，请使用 Python 3.12
- 安装包约 480MB，首次下载需要较长时间

## License

MIT
