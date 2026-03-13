"""
系统托盘管理程序
常驻系统右下角，提供状态查看、换绑 API、手动重启等功能
"""

import os
import sys
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import logging
import subprocess
import platform

# 项目路径
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_DIR)

from tray_manager.guardian import (
    is_gateway_running, start_gateway, get_today_stats,
    send_notification, record_crash, LOG_DIR
)
from tray_manager.updater import check_update, download_and_apply_update

logger = logging.getLogger("tray_app")

APP_NAME = "OpenClaw 管家"  # 替换为你的品牌名
GATEWAY_PORT = 18789
MANAGER_DIR = os.path.expanduser("~/.openclaw-manager")
UPDATE_CHECK_INTERVAL = 3600   # 1小时检查一次更新


class TrayApplication:
    def __init__(self):
        self.running = True
        self.last_collection_time = 0
        self.last_update_check_time = 0
        self.tray_icon = None

    def start(self):
        """启动托盘程序"""
        logger.info(f"{APP_NAME} 托盘程序启动")

        # 启动后台线程
        threading.Thread(target=self._background_loop, daemon=True).start()

        # 启动托盘图标
        self._start_tray()

    def _start_tray(self):
        """创建系统托盘图标"""
        try:
            import pystray
            from PIL import Image

            # 尝试加载自定义图标（搜索多个可能的路径）
            image = None
            # PyInstaller 打包后的资源路径
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
            icon_search_paths = [
                os.path.join(base_path, "assets", "icon.ico"),
                os.path.join(base_path, "assets", "icon.png"),
                os.path.join(PROJECT_DIR, "assets", "icon.ico"),
                os.path.join(PROJECT_DIR, "assets", "icon.png"),
                os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"),
                os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png"),
                os.path.join(MANAGER_DIR, "icon.ico"),
                os.path.join(MANAGER_DIR, "icon.png"),
            ]

            for icon_path in icon_search_paths:
                if os.path.exists(icon_path):
                    try:
                        image = Image.open(icon_path)
                        image = image.resize((64, 64), Image.LANCZOS)
                        break
                    except Exception:
                        continue

            if image is None:
                # 回退：创建红色龙虾简易图标
                image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                from PIL import ImageDraw
                draw = ImageDraw.Draw(image)
                draw.ellipse([8, 8, 56, 56], fill=(230, 80, 40, 255))  # 红色
                draw.text((22, 18), "OC", fill="white")

            menu = pystray.Menu(
                pystray.MenuItem("打开 OpenClaw Web 界面", self._open_web_ui),
                pystray.MenuItem("打开状态面板", self._open_status_panel),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("换绑 API Key", self._open_api_switcher),
                pystray.MenuItem("重启 Gateway", self._restart_gateway),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("查看日志", self._open_log_folder),
                pystray.MenuItem("设置", self._open_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f"退出 {APP_NAME}", self._quit),
            )

            self.tray_icon = pystray.Icon(
                APP_NAME,
                image,
                APP_NAME,
                menu
            )

            self.tray_icon.run()

        except ImportError:
            logger.warning("pystray 或 PIL 未安装，使用简化模式")
            self._run_simple_mode()

    def _run_simple_mode(self):
        """简化模式（无托盘图标时使用）"""
        logger.info("运行在简化模式（无托盘图标）")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False

    def _background_loop(self):
        """
        后台循环：Gateway 守护 + 定时数据采集
        守护逻辑直接集成在托盘 exe 内部，不依赖外部 Python 或 PM2 托管脚本
        """
        CHECK_INTERVAL = 15  # 秒，Gateway 检测间隔
        MAX_RESTART_PER_HOUR = 10
        restart_times = []
        check_counter = 0

        # 首次启动检测
        if not is_gateway_running():
            logger.info("首次检测: Gateway 未运行，正在启动...")
            start_gateway()

        while self.running:
            try:
                time.sleep(CHECK_INTERVAL)
                check_counter += 1

                # ===== 守护逻辑：每次循环都检测 Gateway =====
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
                        time.sleep(600)
                        restart_times.clear()
                        continue

                    # 记录崩溃
                    record_crash({
                        "time": now.isoformat(),
                        "type": "gateway_down",
                        "auto_restart": True,
                    })

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

                # ===== 自动更新：每1小时检查一次 =====
                now_ts = time.time()
                if now_ts - self.last_update_check_time > UPDATE_CHECK_INTERVAL:
                    logger.info("检查更新...")
                    try:
                        update_info = check_update()
                        if update_info and update_info.get("has_update"):
                            version = update_info["version"]
                            logger.info(f"发现新版本: v{version}")
                            send_notification(
                                f"【{APP_NAME}】发现新版本",
                                f"v{version} 可用，正在自动更新..."
                            )
                            success = download_and_apply_update(
                                update_info,
                                notify_callback=lambda msg: send_notification(APP_NAME, msg)
                            )
                            if success:
                                logger.info("更新下载完成，即将重启")
                                self.running = False
                                if self.tray_icon:
                                    self.tray_icon.stop()
                                return
                    except Exception as e:
                        logger.error(f"更新检查异常: {e}")
                    self.last_update_check_time = now_ts

            except Exception as e:
                logger.error(f"后台循环异常: {e}")
                time.sleep(30)

    # ==================== 菜单操作 ====================

    def _open_web_ui(self, icon=None, item=None):
        """打开 OpenClaw Web 界面"""
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{GATEWAY_PORT}")

    def _open_status_panel(self, icon=None, item=None):
        """打开状态面板"""
        threading.Thread(target=self._show_status_window, daemon=True).start()

    def _open_api_switcher(self, icon=None, item=None):
        """打开 API 换绑界面"""
        threading.Thread(target=self._show_api_switcher_window, daemon=True).start()

    def _restart_gateway(self, icon=None, item=None):
        """手动重启 Gateway"""
        logger.info("用户手动重启 Gateway")
        threading.Thread(target=self._do_restart, daemon=True).start()

    def _do_restart(self):
        """执行重启"""
        # 先停止
        try:
            oc_cmd = os.path.join(os.environ.get("APPDATA", ""), "npm", "openclaw.cmd") if platform.system() == "Windows" else "openclaw"
            subprocess.run([oc_cmd, "gateway", "stop"],
                           capture_output=True, timeout=10,
                           encoding="utf-8", errors="replace")
        except Exception:
            pass

        time.sleep(2)
        success = start_gateway()

        if success:
            from tray_manager.guardian import send_notification
            send_notification(APP_NAME, "Gateway 已手动重启成功")
        else:
            from tray_manager.guardian import send_notification
            send_notification(APP_NAME, "Gateway 重启失败，请检查配置")

    def _open_log_folder(self, icon=None, item=None):
        """打开日志文件夹"""
        os.makedirs(LOG_DIR, exist_ok=True)
        if platform.system() == "Windows":
            os.startfile(LOG_DIR)
        elif platform.system() == "Darwin":
            subprocess.run(["open", LOG_DIR])
        else:
            subprocess.run(["xdg-open", LOG_DIR])

    def _open_settings(self, icon=None, item=None):
        """打开设置窗口"""
        threading.Thread(target=self._show_settings_window, daemon=True).start()

    def _quit(self, icon=None, item=None):
        """退出托盘程序"""
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()

    # ==================== 状态面板窗口 ====================

    def _show_status_window(self):
        """显示状态面板"""
        win = tk.Tk()
        win.title(f"{APP_NAME} - 状态面板")
        win.geometry("450x400")
        win.resizable(False, False)

        # 居中
        win.update_idletasks()
        x = (win.winfo_screenwidth() - 450) // 2
        y = (win.winfo_screenheight() - 400) // 2
        win.geometry(f"+{x}+{y}")

        frame = tk.Frame(win, padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="状态面板", font=("微软雅黑", 14, "bold")).pack(pady=(0, 15))

        # 收集状态信息
        gateway_running = is_gateway_running()
        stats = get_today_stats()

        # 读取配置
        config = {}
        config_file = os.path.join(MANAGER_DIR, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except Exception:
                pass

        # OpenClaw 版本
        oc_version = "未安装"
        try:
            oc_cmd = "openclaw.cmd" if platform.system() == "Windows" else "openclaw"
            result = subprocess.run(
                [oc_cmd, "--version"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                oc_version = result.stdout.strip()
        except Exception:
            pass

        # 状态条目
        status_items = [
            ("Gateway 状态",
             "🟢 运行中" if gateway_running else "🔴 已停止",
             "#4CAF50" if gateway_running else "#F44336"),
            ("当前模型", config.get("model", "未配置"), "#333"),
            ("OpenClaw 版本", oc_version, "#333"),
            ("今日自动恢复", f"{stats['crash_count']} 次", "#333"),
            ("Web 界面", f"http://127.0.0.1:{GATEWAY_PORT}", "#2196F3"),
        ]

        for label_text, value_text, color in status_items:
            row = tk.Frame(frame)
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=f"{label_text}:", font=("微软雅黑", 10),
                     width=14, anchor="e").pack(side=tk.LEFT)
            tk.Label(row, text=f"  {value_text}", font=("微软雅黑", 10),
                     fg=color, anchor="w").pack(side=tk.LEFT, fill=tk.X)

        tk.Frame(frame).pack(pady=10)

        # 快捷操作按钮
        btn_frame = tk.Frame(frame)
        btn_frame.pack()

        tk.Button(btn_frame, text="打开 Web 界面", width=14,
                  command=lambda: self._open_web_ui()).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="重启 Gateway", width=14,
                  command=lambda: self._restart_gateway()).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="换绑 API", width=14,
                  command=lambda: self._open_api_switcher()).pack(side=tk.LEFT, padx=3)

        tk.Button(frame, text="刷新", width=10,
                  command=lambda: [win.destroy(), self._open_status_panel()]).pack(pady=10)

        win.mainloop()

    # ==================== API 换绑窗口 ====================

    def _show_api_switcher_window(self):
        """显示 API 换绑界面（根据提供商类型动态显示/隐藏 URL 输入框）"""
        try:
            from installer.core.api_validator import (
                MODEL_PROVIDERS, get_provider_list, get_default_model,
                get_provider_info, validate_api_key
            )
            from installer.core.openclaw_installer import (
                write_config_via_cli, PROVIDER_CONFIG_MAP
            )
        except ImportError as e:
            logger.error(f"无法导入安装器模块: {e}")
            try:
                messagebox.showerror("错误", f"无法打开换绑界面：缺少安装器模块\n{e}")
            except Exception:
                pass
            return

        win = tk.Tk()
        win.title(f"{APP_NAME} - 换绑 API Key")
        win.geometry("500x420")
        win.resizable(False, False)

        win.update_idletasks()
        x = (win.winfo_screenwidth() - 500) // 2
        y = (win.winfo_screenheight() - 420) // 2
        win.geometry(f"+{x}+{y}")

        frame = tk.Frame(win, padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="换绑 API Key", font=("微软雅黑", 14, "bold")).pack(pady=(0, 15))

        # 品牌选择
        tk.Label(frame, text="大模型品牌:", font=("微软雅黑", 10)).pack(anchor="w")
        providers = get_provider_list()
        provider_names = [p["name"] for p in providers]
        provider_keys = [p["key"] for p in providers]

        provider_var = tk.StringVar()
        provider_combo = ttk.Combobox(frame, textvariable=provider_var,
                                       values=provider_names, state="readonly", width=40)
        provider_combo.pack(pady=(3, 8))

        # API URL（放入可隐藏的 frame）
        url_frame = tk.Frame(frame)
        tk.Label(url_frame, text="API URL:", font=("微软雅黑", 10)).pack(anchor="w")
        url_entry = tk.Entry(url_frame, font=("Consolas", 10), width=45)
        url_entry.pack(pady=(3, 8), ipady=3)

        # API Key（放入可隐藏的 frame）
        key_frame = tk.Frame(frame)
        key_frame.pack(fill=tk.X)
        tk.Label(key_frame, text="API Key:", font=("微软雅黑", 10)).pack(anchor="w")
        key_entry = tk.Entry(key_frame, font=("Consolas", 10), width=45, show="*")
        key_entry.pack(pady=(3, 8), ipady=3)

        # 显示/隐藏 Key
        show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(key_frame, text="显示 Key", variable=show_key_var,
                       command=lambda: key_entry.config(show="" if show_key_var.get() else "*")).pack(anchor="w")

        status_label = tk.Label(frame, text="", font=("微软雅黑", 10), wraplength=400)
        status_label.pack(pady=5)

        # 记录选择的品牌
        selected = {"provider_key": "", "model": ""}

        def on_provider_change(event=None):
            idx = provider_combo.current()
            if idx < 0:
                return
            pk = provider_keys[idx]
            selected["provider_key"] = pk
            selected["model"] = get_default_model(pk)

            # 动态显示/隐藏 URL 输入框
            pinfo = get_provider_info(pk)
            need_url = pinfo.get("need_url", False)

            if need_url:
                url_frame.pack(fill=tk.X, before=key_frame)
                url_entry.delete(0, tk.END)
                pconfig = PROVIDER_CONFIG_MAP.get(pk, {})
                default_url = pconfig.get("base_url", "")
                if default_url:
                    url_entry.insert(0, default_url)
            else:
                url_frame.pack_forget()
                url_entry.delete(0, tk.END)

            # Ollama 不需要 Key
            if pk == "ollama":
                key_frame.pack_forget()
            else:
                if not key_frame.winfo_ismapped():
                    key_frame.pack(fill=tk.X, before=status_label)

        provider_combo.bind("<<ComboboxSelected>>", on_provider_change)

        def do_switch():
            try:
                if not selected["provider_key"]:
                    status_label.config(text="请选择品牌", fg="red")
                    return

                pk = selected["provider_key"]
                pinfo = get_provider_info(pk)
                need_url = pinfo.get("need_url", False)
                is_ollama = pk == "ollama"

                url = url_entry.get().strip()
                if need_url and not url:
                    status_label.config(text="请输入 API URL", fg="red")
                    return

                api_key = key_entry.get().strip()
                if not is_ollama and not api_key:
                    status_label.config(text="请输入 API Key", fg="red")
                    return

                status_label.config(text="正在验证...", fg="#2196F3")
                win.update()

                # 验证
                result = validate_api_key(
                    provider_key=pk,
                    endpoint_name="默认",
                    api_key=api_key,
                    model=selected["model"],
                    custom_url=url if url else None,
                )

                if result["valid"]:
                    # 写入配置
                    write_result = write_config_via_cli(
                        pk,
                        selected["model"],
                        api_key,
                        url if url else None,
                    )

                    if write_result["success"]:
                        status_label.config(text="换绑成功！正在重启 Gateway...", fg="green")
                        win.update()

                        # 更新本地配置
                        mgr_config_file = os.path.join(MANAGER_DIR, "config.json")
                        mgr_config = {}
                        if os.path.exists(mgr_config_file):
                            try:
                                with open(mgr_config_file, 'r') as f:
                                    mgr_config = json.load(f)
                            except Exception:
                                pass
                        mgr_config["provider"] = pk
                        mgr_config["model"] = selected["model"]
                        with open(mgr_config_file, 'w') as f:
                            json.dump(mgr_config, f, indent=2)

                        # 重启 Gateway（完成后更新状态标签）
                        def restart_and_update():
                            self._do_restart()
                            try:
                                status_label.config(text="换绑成功！Gateway 已重启", fg="green")
                            except Exception:
                                pass
                        threading.Thread(target=restart_and_update, daemon=True).start()
                    else:
                        status_label.config(text=f"配置写入失败: {write_result['message']}", fg="red")
                else:
                    status_label.config(text=f"{result['message']}", fg="red")
            except Exception as e:
                logger.error(f"换绑异常: {e}")
                status_label.config(text=f"验证出错: {str(e)[:80]}", fg="red")

        tk.Button(frame, text="验证并换绑", font=("微软雅黑", 11),
                  width=20, command=do_switch,
                  bg="#4CAF50", fg="white", relief=tk.FLAT).pack(pady=10)

        win.mainloop()

    # ==================== 设置窗口 ====================

    def _show_settings_window(self):
        """显示设置窗口"""
        win = tk.Tk()
        win.title(f"{APP_NAME} - 设置")
        win.geometry("400x250")
        win.resizable(False, False)

        win.update_idletasks()
        x = (win.winfo_screenwidth() - 400) // 2
        y = (win.winfo_screenheight() - 250) // 2
        win.geometry(f"+{x}+{y}")

        frame = tk.Frame(win, padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="设置", font=("微软雅黑", 14, "bold")).pack(pady=(0, 15))

        # 读取当前配置
        config_file = os.path.join(MANAGER_DIR, "config.json")
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except Exception:
                pass

        # 开机自启开关
        autostart_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame, text="开机自动启动",
            variable=autostart_var, font=("微软雅黑", 10)
        ).pack(anchor="w", pady=5)

        def save_settings():
            os.makedirs(MANAGER_DIR, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("提示", "设置已保存")
            win.destroy()

        tk.Button(frame, text="保存设置", font=("微软雅黑", 11),
                  width=15, command=save_settings,
                  bg="#4CAF50", fg="white", relief=tk.FLAT).pack(pady=20)

        win.mainloop()


def main():
    """托盘程序入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(
                os.path.join(LOG_DIR, "tray.log"), encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )
    os.makedirs(LOG_DIR, exist_ok=True)

    app = TrayApplication()
    app.start()


if __name__ == "__main__":
    main()
