"""
自动更新模块
定期检查服务器上的最新版本，有更新时自动下载并替换
"""

import os
import sys
import json
import logging
import urllib.request
import shutil
import subprocess
import platform
import tempfile

logger = logging.getLogger("updater")

SERVER_URL = os.environ.get("OPENCLAW_SERVER_URL", "http://localhost:8000")
CURRENT_VERSION = "1.0.0"
MANAGER_DIR = os.path.expanduser("~/.openclaw-manager")


def check_update() -> dict | None:
    """
    检查服务器上是否有新版本
    返回: {"has_update": bool, "version": str, "url": str, "changelog": str} 或 None
    """
    try:
        response = urllib.request.urlopen(f"{SERVER_URL}/version", timeout=10)
        data = json.loads(response.read().decode())

        server_version = data.get("tray_version", "1.0.0")

        if _version_gt(server_version, CURRENT_VERSION):
            return {
                "has_update": True,
                "version": server_version,
                "url": f"{SERVER_URL}{data.get('update_url', '/static/OpenClaw-Tray.exe')}",
                "changelog": data.get("changelog", ""),
            }
        else:
            return {"has_update": False, "version": server_version}

    except Exception as e:
        logger.debug(f"检查更新失败: {e}")
        return None


def _version_gt(v1: str, v2: str) -> bool:
    """比较版本号 v1 > v2"""
    try:
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        return parts1 > parts2
    except Exception:
        return v1 != v2


def download_and_apply_update(update_info: dict, notify_callback=None) -> bool:
    """
    下载新版本并替换当前程序
    返回是否成功
    """
    try:
        url = update_info["url"]
        version = update_info["version"]

        if notify_callback:
            notify_callback(f"正在下载更新 v{version}...")

        # 下载到临时文件
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "OpenClaw-Tray_new.exe")

        urllib.request.urlretrieve(url, temp_file)

        # 验证下载的文件
        file_size = os.path.getsize(temp_file)
        if file_size < 1024 * 100:  # 小于100KB说明下载失败
            logger.error(f"下载的文件太小: {file_size} bytes")
            return False

        # 获取当前 exe 的路径
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            current_exe = os.path.join(MANAGER_DIR, "OpenClaw-Tray.exe")

        # 创建更新脚本（因为正在运行的 exe 无法直接替换自己）
        update_script = os.path.join(temp_dir, "update.bat")
        with open(update_script, 'w') as f:
            f.write(f'''@echo off
timeout /t 3 /nobreak >nul
copy /Y "{temp_file}" "{current_exe}"
start "" "{current_exe}"
del "{temp_file}"
del "{update_script}"
rmdir "{temp_dir}"
''')

        if notify_callback:
            notify_callback(f"更新 v{version} 已下载，重启后生效")

        # 保存新版本号
        version_file = os.path.join(MANAGER_DIR, "version.json")
        with open(version_file, 'w') as f:
            json.dump({"version": version, "updated_at": ""}, f)

        # 执行更新脚本并退出当前程序
        if platform.system() == "Windows":
            subprocess.Popen(
                ["cmd", "/c", update_script],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        return True

    except Exception as e:
        logger.error(f"更新失败: {e}")
        return False


def get_current_version() -> str:
    """获取当前版本号"""
    version_file = os.path.join(MANAGER_DIR, "version.json")
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get("version", CURRENT_VERSION)
        except Exception:
            pass
    return CURRENT_VERSION
