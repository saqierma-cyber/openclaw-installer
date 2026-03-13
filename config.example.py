# ==================== 配置示例 ====================
# 复制此文件为 config.py，填写你的实际配置
#
# 需要修改的文件和变量：
#
# 1. installer/core/activator.py
#    SERVER_URL = "http://YOUR_SERVER_IP:8000"
#    SECRET_KEY = "your_random_secret_key_here"
#
# 2. installer/core/openclaw_installer.py (install_openclaw 函数内)
#    OPENCLAW_TGZ_URL = "http://YOUR_SERVER_IP:8000/static/openclaw-full.tgz"
#
# 3. installer/main.py (_step_install_tray 函数内)
#    TRAY_EXE_URL = "http://YOUR_SERVER_IP:8000/static/OpenClaw-Tray.exe"
#
# ==================== 服务器搭建指南 ====================
#
# 推荐配置：
#   - 系统: Ubuntu 22.04 LTS
#   - CPU: 1 核
#   - 内存: 1~2 GB
#   - 硬盘: 20 GB SSD（安装包约 500MB）
#   - 框架: Python FastAPI + SQLite
#   - Web: Nginx 反向代理 + Uvicorn
#
# 服务器需要提供以下 API：
#   POST /api/v1/activate    — 验证激活码
#   GET  /static/*.tgz       — 下载 OpenClaw 安装包
#   GET  /static/*.exe       — 下载托盘管家
#   GET  /health             — 健康检查
#   GET  /version            — 版本信息（用于自动更新）
#
# ==================== 在服务器上预打包 OpenClaw ====================
#
# 1. 在服务器上全局安装 OpenClaw：
#    npm install -g openclaw@latest
#
# 2. 找到安装目录并打包：
#    cd $(npm root -g)
#    tar -czf /opt/openclaw-server/static/openclaw-full.tgz openclaw/
#
# 3. 确保 FastAPI 挂载了静态文件目录：
#    from fastapi.staticfiles import StaticFiles
#    app.mount("/static", StaticFiles(directory="static"), name="static")
