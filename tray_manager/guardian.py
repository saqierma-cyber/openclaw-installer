"""
OpenClaw Gateway 守护脚本
由 PM2 托管，持续监控 Gateway 状态，崩溃时自动重启并发送品牌通知
"""

import subprocess
import platform
import time
import os
import json
import logging
from datetime import datetime

# ==================== 配置 ====================
APP_NAME = "OpenClaw 管家"  # 替换为你的品牌名
GATEWAY_PORT = 18789
CHECK_INTERVAL = 15  # 秒，检测间隔
MAX_RESTART_PER_HOUR = 10  # 每小时最大重启次数（防止无限重启）
LOG_DIR = os.path.expanduser("~/.openclaw-manager/logs")
LOG_FILE = os.path.join(LOG_DIR, "guardian.log")

# ==================== 日志配置 ====================
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("guardian")


def _run_cmd(cmd, timeout=30, shell=False):
    """运行命令"""
    extra = {}
    if platform.system() == "Windows":
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=shell,
            encoding="utf-8", errors="replace",
            **extra
        )
    except Exception as e:
        logger.error(f"命令执行失败 {cmd}: {e}")
        return None


def is_gateway_running() -> bool:
    """检测 Gateway 是否在运行"""
    # 方法1: 通过端口检测
    try:
        import urllib.request
        req = urllib.request.urlopen(
            f"http://127.0.0.1:{GATEWAY_PORT}/health",
            timeout=5
        )
        return req.status == 200
    except Exception:
        pass

    # 方法2: 通过进程检测
    try:
        if platform.system() == "Windows":
            result = _run_cmd(["tasklist", "/FI", "IMAGENAME eq node.exe"], timeout=10)
        else:
            result = _run_cmd(["pgrep", "-f", "openclaw"], timeout=10)

        if result and result.returncode == 0 and "openclaw" in (result.stdout or "").lower():
            return True
    except Exception:
        pass

    return False


def start_gateway() -> bool:
    """启动 Gateway（使用完整路径 + PowerShell Start-Process）"""
    logger.info("正在启动 OpenClaw Gateway...")
    try:
        if platform.system() == "Windows":
            import shutil
            # 直接构建完整路径
            oc_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "openclaw.cmd")
            if not os.path.exists(oc_path):
                oc_path = shutil.which("openclaw.cmd") or shutil.which("openclaw") or ""
            if not oc_path:
                logger.error("找不到 openclaw.cmd")
                return False

            subprocess.Popen(
                ["powershell", "-Command",
                 f'Start-Process -FilePath "{oc_path}" -ArgumentList "gateway","--port","{GATEWAY_PORT}" -WindowStyle Minimized'],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen(
                ["openclaw", "gateway", "--port", str(GATEWAY_PORT)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        # 等待启动
        for i in range(10):
            time.sleep(2)
            if is_gateway_running():
                logger.info("Gateway 启动成功")
                return True

        logger.warning("Gateway 启动超时")
        return False

    except Exception as e:
        logger.error(f"Gateway 启动失败: {e}")
        return False


def send_notification(title: str, message: str):
    """发送 Windows 系统通知"""
    try:
        if platform.system() == "Windows":
            # 尝试使用 win10toast
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=5, threaded=True)
                return
            except ImportError:
                pass

            # 回退: 使用 PowerShell
            ps_cmd = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $template.GetElementsByTagName('text')[0].AppendChild($template.CreateTextNode('{title}')) > $null
            $template.GetElementsByTagName('text')[1].AppendChild($template.CreateTextNode('{message}')) > $null
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('OpenClaw Manager').Show($template)
            """
            _run_cmd(["powershell", "-Command", ps_cmd], timeout=10)

        elif platform.system() == "Darwin":
            _run_cmd([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"'
            ])

    except Exception as e:
        logger.error(f"通知发送失败: {e}")


def record_crash(crash_info: dict):
    """记录崩溃信息到日志文件"""
    crash_log_file = os.path.join(LOG_DIR, "crashes.json")
    crashes = []

    if os.path.exists(crash_log_file):
        try:
            with open(crash_log_file, 'r', encoding='utf-8') as f:
                crashes = json.load(f)
        except Exception:
            crashes = []

    crashes.append(crash_info)

    # 只保留最近100条
    crashes = crashes[-100:]

    with open(crash_log_file, 'w', encoding='utf-8') as f:
        json.dump(crashes, f, indent=2, ensure_ascii=False)


def get_today_stats() -> dict:
    """获取今日统计"""
    crash_log_file = os.path.join(LOG_DIR, "crashes.json")
    today = datetime.now().strftime("%Y-%m-%d")
    today_crashes = 0

    if os.path.exists(crash_log_file):
        try:
            with open(crash_log_file, 'r', encoding='utf-8') as f:
                crashes = json.load(f)
            today_crashes = sum(1 for c in crashes if c.get("time", "").startswith(today))
        except Exception:
            pass

    return {"date": today, "crash_count": today_crashes}


def main_loop():
    """主守护循环"""
    logger.info(f"=== {APP_NAME} 守护脚本启动 ===")
    logger.info(f"监控端口: {GATEWAY_PORT}, 检测间隔: {CHECK_INTERVAL}秒")

    restart_times = []  # 记录重启时间，用于限频

    # 首次启动检测
    if not is_gateway_running():
        logger.info("首次检测: Gateway 未运行，正在启动...")
        start_gateway()

    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            if not is_gateway_running():
                now = datetime.now()
                logger.warning(f"检测到 Gateway 已停止运行! ({now.isoformat()})")

                # 限频检查
                one_hour_ago = time.time() - 3600
                restart_times = [t for t in restart_times if t > one_hour_ago]

                if len(restart_times) >= MAX_RESTART_PER_HOUR:
                    logger.error(f"一小时内已重启 {len(restart_times)} 次，暂停重启")
                    send_notification(
                        APP_NAME,
                        "Gateway 频繁崩溃，已暂停自动恢复，请检查配置"
                    )
                    time.sleep(600)  # 等10分钟
                    restart_times.clear()
                    continue

                # 记录崩溃
                crash_info = {
                    "time": now.isoformat(),
                    "type": "gateway_down",
                    "auto_restart": True,
                }
                record_crash(crash_info)

                # 尝试重启
                success = start_gateway()
                restart_times.append(time.time())

                if success:
                    stats = get_today_stats()
                    send_notification(
                        f"【{APP_NAME}】已自动恢复",
                        f"Gateway 异常已修复，今日自动恢复 {stats['crash_count']} 次"
                    )
                    logger.info("Gateway 重启成功")
                else:
                    send_notification(
                        f"【{APP_NAME}】恢复失败",
                        "Gateway 重启失败，请打开管理面板检查"
                    )
                    logger.error("Gateway 重启失败")

        except KeyboardInterrupt:
            logger.info("守护脚本收到退出信号")
            break
        except Exception as e:
            logger.error(f"守护循环异常: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main_loop()
