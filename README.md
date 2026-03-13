# OpenClaw 一键安装工具

> 让 [OpenClaw](https://github.com/openclaw/openclaw) AI 助手的部署变得简单——双击 exe，输入激活码和 API Key，自动完成全部配置。

## 功能

- **一键安装**：自动检测/安装 Node.js，下载 OpenClaw 并配置
- **多品牌适配**：支持 OpenAI、Anthropic、Google Gemini、Kimi Coding、MiniMax 等 20+ 模型提供商
- **托盘管家**：常驻系统托盘，Gateway 崩溃自动恢复，支持换绑 API Key
- **自动更新**：托盘管家定时检查新版本

## 项目结构

```
├── installer/          # 安装器 GUI（打包成 OpenClaw-Installer.exe）
│   ├── main.py        # tkinter 向导界面
│   └── core/          # 激活码验证、API 验证、Node.js 安装、OpenClaw 配置
├── tray_manager/       # 托盘管家（打包成 OpenClaw-Tray.exe）
│   ├── main.py        # 系统托盘 + 状态面板 + 换绑 API
│   ├── guardian.py    # Gateway 守护（崩溃检测 + 自动重启）
│   └── updater.py     # 自动更新
├── server/             # 验证服务器（FastAPI）
│   ├── main.py        # 服务器入口
│   ├── routes/        # API 路由
│   ├── models/        # 数据库
│   └── utils/         # 签名工具 + 激活码生成
└── assets/             # 图标资源
```

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env`，填写你的服务器信息：

```bash
cp .env.example .env
```

### 2. 部署验证服务器

```bash
cd server
pip install fastapi uvicorn
python main.py
```

### 3. 打包安装器

需要 Python 3.12 + PyInstaller：

```powershell
# 安装器
py -3.12 -m PyInstaller --onefile --windowed --name "OpenClaw-Installer" --icon assets/icon.ico --paths installer --hidden-import core.activator --hidden-import core.api_validator --hidden-import core.fingerprint --hidden-import core.node_installer --hidden-import core.openclaw_installer installer/main.py --noconfirm --clean

# 托盘管家
py -3.12 -m PyInstaller --onefile --windowed --name "OpenClaw-Tray" --icon assets/icon.ico --add-data "assets;assets" --paths tray_manager --hidden-import guardian --hidden-import data_collector --hidden-import updater tray_manager/main.py --noconfirm --clean
```

### 4. 生成激活码

```bash
cd server
python utils/code_generator.py --count 10 --valid-hours 720
```

## 技术栈

- **客户端**：Python 3.12 + tkinter + pystray + PyInstaller
- **服务器**：FastAPI + SQLite + Uvicorn
- **签名**：HMAC-SHA256

## License

MIT
