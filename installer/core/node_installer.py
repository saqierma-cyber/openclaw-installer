"""
Node.js 安装器
检测系统是否有 Node.js >= 22，没有则自动安装
"""

import subprocess
import platform
import os
import sys
import shutil
import re
import urllib.request
import tempfile

# Node.js 22 下载地址（部署前请确认最新版本号）
NODE_MSI_URL = "https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi"
NODE_MSI_FILENAME = "node-v22-x64.msi"
REQUIRED_MAJOR_VERSION = 22


def _run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """运行命令，Windows 下隐藏窗口"""
    extra = {}
    if platform.system() == "Windows":
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **extra, **kwargs)


def check_node_installed() -> dict:
    """
    检测 Node.js 是否已安装
    返回: {"installed": bool, "version": str, "meets_requirement": bool}
    """
    try:
        result = _run_cmd(["node", "--version"])
        if result.returncode == 0:
            version_str = result.stdout.strip()  # e.g., "v22.14.0"
            match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', version_str)
            if match:
                major = int(match.group(1))
                return {
                    "installed": True,
                    "version": version_str,
                    "major": major,
                    "meets_requirement": major >= REQUIRED_MAJOR_VERSION,
                }
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return {"installed": False, "version": "", "major": 0, "meets_requirement": False}


def check_npm_installed() -> bool:
    """检测 npm 是否可用"""
    try:
        result = _run_cmd(["npm", "--version"])
        return result.returncode == 0
    except Exception:
        return False


def get_embedded_msi_path() -> str | None:
    """
    获取内嵌在 exe 中的 Node.js msi 路径
    PyInstaller 打包后资源在 sys._MEIPASS 目录
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包模式
        msi_path = os.path.join(sys._MEIPASS, "resources", NODE_MSI_FILENAME)
    else:
        # 开发模式
        msi_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "resources",
            NODE_MSI_FILENAME
        )

    if os.path.exists(msi_path):
        return msi_path
    return None


def download_node_msi(progress_callback=None) -> str:
    """
    下载 Node.js msi 安装包
    progress_callback: 可选的进度回调 callback(downloaded_mb, total_mb)
    返回: msi 文件路径
    """
    temp_dir = tempfile.mkdtemp()
    msi_path = os.path.join(temp_dir, NODE_MSI_FILENAME)

    def reporthook(block_num, block_size, total_size):
        if progress_callback and total_size > 0:
            downloaded = block_num * block_size
            progress_callback(downloaded / 1024 / 1024, total_size / 1024 / 1024)

    urllib.request.urlretrieve(NODE_MSI_URL, msi_path, reporthook=reporthook)
    return msi_path


def install_node_windows(msi_path: str, progress_callback=None) -> dict:
    """
    在 Windows 上静默安装 Node.js
    需要管理员权限
    返回: {"success": bool, "message": str}
    """
    if not os.path.exists(msi_path):
        return {"success": False, "message": f"安装包不存在: {msi_path}"}

    try:
        if progress_callback:
            progress_callback("正在安装 Node.js，请稍候...")

        # 静默安装
        result = subprocess.run(
            ["msiexec", "/i", msi_path, "/qn", "/norestart",
             "ADDLOCAL=ALL"],
            capture_output=True, text=True, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )

        if result.returncode == 0:
            # 刷新环境变量
            _refresh_path_windows()
            return {"success": True, "message": "Node.js 安装成功"}
        elif result.returncode == 1603:
            return {"success": False, "message": "安装失败，请以管理员身份运行本程序"}
        else:
            return {"success": False,
                    "message": f"安装失败 (错误码: {result.returncode})，请以管理员身份运行"}

    except subprocess.TimeoutExpired:
        return {"success": False, "message": "安装超时，请手动安装 Node.js"}
    except Exception as e:
        return {"success": False, "message": f"安装出错: {str(e)}"}


def _refresh_path_windows():
    """刷新 Windows 环境变量（让新安装的 node/npm 立即可用）"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            system_path = winreg.QueryValueEx(key, "Path")[0]

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                user_path = winreg.QueryValueEx(key, "Path")[0]
            except FileNotFoundError:
                user_path = ""

        os.environ["PATH"] = f"{system_path};{user_path}"
    except Exception:
        # 如果刷新失败，添加常见的 Node.js 路径
        node_paths = [
            r"C:\Program Files\nodejs",
            os.path.expandvars(r"%APPDATA%\npm"),
        ]
        current_path = os.environ.get("PATH", "")
        for p in node_paths:
            if p not in current_path:
                os.environ["PATH"] = f"{p};{current_path}"
                current_path = os.environ["PATH"]


def install_node(progress_callback=None) -> dict:
    """
    完整的 Node.js 安装流程
    1. 检测是否已安装
    2. 如果没有或版本太低，尝试用内嵌的 msi 安装
    3. 如果没有内嵌 msi，从网上下载
    
    返回: {"success": bool, "message": str, "version": str}
    """
    # 检测现有安装
    node_info = check_node_installed()
    if node_info["meets_requirement"]:
        return {
            "success": True,
            "message": f"Node.js {node_info['version']} 已安装，满足要求",
            "version": node_info["version"]
        }

    if node_info["installed"]:
        msg = f"当前 Node.js 版本 {node_info['version']} 过低，需要 v{REQUIRED_MAJOR_VERSION}+，正在升级..."
    else:
        msg = f"未检测到 Node.js，正在安装 v{REQUIRED_MAJOR_VERSION}..."

    if progress_callback:
        progress_callback(msg)

    system = platform.system()
    if system != "Windows":
        return {"success": False, "message": "当前版本仅支持 Windows", "version": ""}

    # 尝试使用内嵌的 msi
    msi_path = get_embedded_msi_path()

    if not msi_path:
        # 从网上下载
        if progress_callback:
            progress_callback("正在下载 Node.js 安装包...")
        try:
            msi_path = download_node_msi(progress_callback)
        except Exception as e:
            return {"success": False, "message": f"下载失败: {str(e)}", "version": ""}

    # 安装
    result = install_node_windows(msi_path, progress_callback)

    if result["success"]:
        # 验证安装
        node_info = check_node_installed()
        if node_info["meets_requirement"]:
            return {
                "success": True,
                "message": f"Node.js {node_info['version']} 安装成功",
                "version": node_info["version"]
            }
        else:
            return {
                "success": False,
                "message": "安装似乎成功但验证失败，请重启电脑后再试",
                "version": ""
            }

    return {"success": False, "message": result["message"], "version": ""}
