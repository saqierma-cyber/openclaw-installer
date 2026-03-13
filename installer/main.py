"""
OpenClaw 一键安装器 - 主 GUI 程序
完整安装向导：激活码 → 模型选择 → API Key → 安装 → 完成
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.activator import verify_activation_code
from core.api_validator import (
    MODEL_PROVIDERS, get_provider_list, get_default_model,
    get_provider_info, get_endpoints, get_endpoint_config, validate_api_key
)
from core.openclaw_installer import PROVIDER_CONFIG_MAP
from core.node_installer import install_node, check_node_installed
from core.openclaw_installer import (
    install_openclaw, write_config_via_cli, install_pm2,
    setup_guardian_service, start_gateway, open_browser, check_openclaw_installed
)


# ==================== 品牌配置 ====================
APP_NAME = "OpenClaw 一键安装工具"  # 替换为你的品牌名
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 500


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.root.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.root.geometry(f"+{x}+{y}")

        # 状态变量
        self.activation_code = ""
        self.selected_provider = ""
        self.selected_endpoint = ""
        self.selected_model = ""
        self.api_key = ""
        self.custom_url = ""

        # 主容器
        self.main_frame = tk.Frame(self.root, padx=30, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 显示欢迎页
        self.show_welcome()

    def clear_frame(self):
        """清空主框架"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def add_title(self, text):
        """添加标题"""
        label = tk.Label(self.main_frame, text=text, font=("微软雅黑", 16, "bold"))
        label.pack(pady=(0, 5))

    def add_subtitle(self, text):
        """添加副标题"""
        label = tk.Label(self.main_frame, text=text, font=("微软雅黑", 10),
                         fg="#666666", wraplength=500)
        label.pack(pady=(0, 20))

    def add_status(self, text, color="#333333"):
        """添加状态文字"""
        label = tk.Label(self.main_frame, text=text, font=("微软雅黑", 10),
                         fg=color, wraplength=500)
        label.pack(pady=5)
        return label

    # ==================== 第1页：欢迎 ====================

    def show_welcome(self):
        self.clear_frame()
        self.add_title(f"欢迎使用 {APP_NAME}")
        self.add_subtitle("本工具将自动为您安装和配置 OpenClaw 个人 AI 助手\n全程自动化，您只需提供激活码和 API Key")

        # 功能列表
        features = [
            "自动安装 Node.js 运行环境",
            "自动安装 OpenClaw 最新版",
            "一键配置大模型 API",
            "自动设置开机自启和崩溃恢复",
        ]
        for feat in features:
            tk.Label(self.main_frame, text=f"  ✓  {feat}",
                     font=("微软雅黑", 10), anchor="w").pack(fill=tk.X, pady=2)

        tk.Frame(self.main_frame).pack(pady=10)

        tk.Button(
            self.main_frame, text="开始安装", font=("微软雅黑", 12),
            width=20, height=2, command=self.show_activation,
            bg="#4CAF50", fg="white", relief=tk.FLAT
        ).pack(pady=20)

    # ==================== 第2页：激活码 ====================

    def show_activation(self):
        self.clear_frame()
        self.add_title("输入激活码")
        self.add_subtitle("请在下方输入框中输入您的激活码")

        tk.Label(self.main_frame, text="激活码:", font=("微软雅黑", 10)).pack(anchor="w")
        self.code_entry = tk.Entry(self.main_frame, font=("Consolas", 14), width=35)
        self.code_entry.pack(pady=(5, 15), ipady=5)
        self.code_entry.focus()

        self.activation_status = self.add_status("")

        btn_frame = tk.Frame(self.main_frame)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="验证激活码", font=("微软雅黑", 11),
                  width=15, command=self.do_activation,
                  bg="#2196F3", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="返回", font=("微软雅黑", 11),
                  width=10, command=self.show_welcome,
                  relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

    def do_activation(self):
        code = self.code_entry.get().strip()
        if not code:
            self.activation_status.config(text="请输入激活码", fg="red")
            return

        self.activation_status.config(text="正在验证...", fg="#2196F3")
        self.root.update()

        def verify():
            result = verify_activation_code(code)
            self.root.after(0, lambda: self._handle_activation_result(code, result))

        threading.Thread(target=verify, daemon=True).start()

    def _handle_activation_result(self, code, result):
        if result["status"] == "success":
            self.activation_code = code
            self.show_model_select()
        else:
            self.activation_status.config(text=result["message"], fg="red")

    # ==================== 第3页：配置大模型（简化版：品牌+URL+Key 一页搞定）====================

    def show_model_select(self):
        self.clear_frame()
        self.add_title("配置 AI 大模型")
        self.add_subtitle("选择品牌，输入 API Key，点击下一步自动验证")

        # 品牌选择
        tk.Label(self.main_frame, text="大模型品牌:", font=("微软雅黑", 10)).pack(anchor="w")
        providers = get_provider_list()
        provider_names = [p["name"] for p in providers]
        self.provider_keys = [p["key"] for p in providers]
        self.provider_infos = {p["key"]: p for p in providers}

        self.provider_var = tk.StringVar()
        self.provider_combo = ttk.Combobox(
            self.main_frame, textvariable=self.provider_var,
            values=provider_names, state="readonly", font=("微软雅黑", 10), width=45
        )
        self.provider_combo.pack(pady=(5, 10))
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # API URL（放入可隐藏的 frame）
        self.url_frame = tk.Frame(self.main_frame)
        self.url_frame.pack(fill=tk.X)
        tk.Label(self.url_frame, text="API URL:", font=("微软雅黑", 10)).pack(anchor="w")
        self.url_entry = tk.Entry(self.url_frame, font=("Consolas", 10), width=50)
        self.url_entry.pack(pady=(5, 10), ipady=3)

        # API Key（放入可隐藏的 frame）
        self.key_frame = tk.Frame(self.main_frame)
        self.key_frame.pack(fill=tk.X)
        tk.Label(self.key_frame, text="API Key:", font=("微软雅黑", 10)).pack(anchor="w")
        self.apikey_entry = tk.Entry(self.key_frame, font=("Consolas", 10), width=50, show="*")
        self.apikey_entry.pack(pady=(5, 5), ipady=3)

        # 显示/隐藏 Key
        self.show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.key_frame, text="显示 Key",
                       variable=self.show_key_var,
                       command=self._toggle_key_visibility).pack(anchor="w")

        # 状态提示
        self.verify_status = self.add_status("")

        # 按钮
        btn_frame = tk.Frame(self.main_frame)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="验证并继续", font=("微软雅黑", 11),
                  width=15, command=self.do_verify_apikey,
                  bg="#4CAF50", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="返回", font=("微软雅黑", 11),
                  width=10, command=self.show_activation,
                  relief=tk.FLAT).pack(side=tk.LEFT, padx=5)

        # 默认隐藏 URL 框（等用户选择品牌后决定）
        self.url_frame.pack_forget()

    def _on_provider_change(self, event=None):
        """选择品牌后，根据 need_url 动态显示/隐藏 URL 输入框"""
        idx = self.provider_combo.current()
        if idx < 0:
            return
        provider_key = self.provider_keys[idx]
        self.selected_provider = provider_key
        self.selected_endpoint = "默认"

        # 记录默认模型
        self.selected_model = get_default_model(provider_key)

        # 获取提供商信息
        provider_info = get_provider_info(provider_key)
        need_url = provider_info.get("need_url", False)
        is_ollama = provider_key == "ollama"

        # 动态显示/隐藏 URL 输入框
        if need_url:
            # 需要 URL：显示并预填默认值
            self.url_frame.pack(fill=tk.X, before=self.key_frame)
            self.url_entry.delete(0, tk.END)
            # 从 PROVIDER_CONFIG_MAP 获取默认 URL
            pconfig = PROVIDER_CONFIG_MAP.get(provider_key, {})
            default_url = pconfig.get("base_url", "")
            if default_url:
                self.url_entry.insert(0, default_url)
        else:
            # 不需要 URL：隐藏
            self.url_frame.pack_forget()
            self.url_entry.delete(0, tk.END)

        # Ollama 不需要 API Key，隐藏 Key 输入框
        if is_ollama:
            self.key_frame.pack_forget()
        else:
            if not self.key_frame.winfo_ismapped():
                self.key_frame.pack(fill=tk.X, before=self.verify_status if hasattr(self, 'verify_status') else None)

    def _toggle_key_visibility(self):
        if self.show_key_var.get():
            self.apikey_entry.config(show="")
        else:
            self.apikey_entry.config(show="*")

    def do_verify_apikey(self):
        """验证 API Key（根据提供商类型走不同逻辑）"""
        if not self.selected_provider:
            self.verify_status.config(text="请先选择大模型品牌", fg="red")
            return

        provider_info = get_provider_info(self.selected_provider)
        need_url = provider_info.get("need_url", False)
        is_ollama = self.selected_provider == "ollama"

        # 获取 URL（仅 need_url=True 时必填）
        self.custom_url = self.url_entry.get().strip()
        if need_url and not self.custom_url:
            self.verify_status.config(text="请输入 API URL", fg="red")
            return

        # 获取 API Key（Ollama 不需要）
        api_key = self.apikey_entry.get().strip()
        if not is_ollama and not api_key:
            self.verify_status.config(text="请输入 API Key", fg="red")
            return

        self.api_key = api_key
        self.verify_status.config(text="正在验证 API Key...", fg="#2196F3")
        self.root.update()

        def verify():
            result = validate_api_key(
                provider_key=self.selected_provider,
                endpoint_name=self.selected_endpoint,
                api_key=api_key,
                model=self.selected_model,
                custom_url=self.custom_url if self.custom_url else None,
            )
            self.root.after(0, lambda: self._handle_apikey_result(result))

        threading.Thread(target=verify, daemon=True).start()

    def _handle_apikey_result(self, result):
        if result["valid"]:
            self.verify_status.config(text="✓ " + result["message"], fg="green")
            self.root.after(1000, self.show_install_progress)
        else:
            self.verify_status.config(text="✗ " + result["message"], fg="red")

    # ==================== 第5页：安装进度 ====================

    def show_install_progress(self):
        self.clear_frame()
        self.add_title("正在安装")
        self.add_subtitle("请稍候，全程自动化，无需操作")

        self.progress_bar = ttk.Progressbar(
            self.main_frame, length=500, mode='determinate'
        )
        self.progress_bar.pack(pady=10)

        self.progress_label = tk.Label(
            self.main_frame, text="准备中...",
            font=("微软雅黑", 10), fg="#333333", wraplength=500
        )
        self.progress_label.pack(pady=5)

        # 日志文本框
        self.log_text = tk.Text(self.main_frame, height=10, width=65,
                                font=("Consolas", 9), state="disabled",
                                bg="#F5F5F5")
        self.log_text.pack(pady=10)

        # 在后台线程执行安装
        threading.Thread(target=self._run_installation, daemon=True).start()

    def _update_progress(self, percent, message):
        """更新进度（线程安全）"""
        def update():
            self.progress_bar["value"] = percent
            self.progress_label.config(text=message)
            self._append_log(message)
        self.root.after(0, update)

    def _append_log(self, text):
        """添加日志"""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"{text}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _run_installation(self):
        """执行完整安装流程"""
        steps = [
            (10, "检测 / 安装 Node.js", self._step_install_node),
            (30, "安装 OpenClaw", self._step_install_openclaw),
            (50, "安装 PM2 进程管理器", self._step_install_pm2),
            (60, "写入模型配置", self._step_write_config),
            (70, "配置守护服务", self._step_setup_guardian),
            (80, "安装托盘管理程序", self._step_install_tray),
            (90, "启动 Gateway", self._step_start_gateway),
            (100, "安装完成", None),
        ]

        for percent, description, step_func in steps:
            self._update_progress(percent, description + "...")
            if step_func:
                result = step_func()
                if not result.get("success", True):
                    self._update_progress(
                        percent,
                        f"❌ {description}失败: {result.get('message', '未知错误')}"
                    )
                    self.root.after(0, lambda msg=result.get("message", ""): self._show_retry(msg))
                    return
                self._update_progress(percent, f"✓ {description} - {result.get('message', '完成')}")

        # 全部成功
        self.root.after(500, self.show_privacy_agreement)

    def _step_install_node(self) -> dict:
        return install_node(progress_callback=lambda msg: self._update_progress(15, str(msg)))

    def _step_install_openclaw(self) -> dict:
        return install_openclaw(progress_callback=lambda msg: self._update_progress(35, str(msg)))

    def _step_install_pm2(self) -> dict:
        return install_pm2(progress_callback=lambda msg: self._update_progress(55, str(msg)))

    def _step_write_config(self) -> dict:
        # 只有用户填了 URL 才传给配置写入
        base_url = self.custom_url if self.custom_url else None
        return write_config_via_cli(
            provider_key=self.selected_provider,
            model_name=self.selected_model,
            api_key=self.api_key,
            base_url=base_url,
        )

    def _step_setup_guardian(self) -> dict:
        return setup_guardian_service()

    def _step_start_gateway(self) -> dict:
        return start_gateway(progress_callback=lambda msg: self._update_progress(92, str(msg)))

    def _step_install_tray(self) -> dict:
        """从服务器下载并部署托盘管理程序"""
        import urllib.request

        TRAY_EXE_URL = os.environ.get("OPENCLAW_TRAY_URL", "http://localhost:8000/static/OpenClaw-Tray.exe")

        try:
            tray_dir = os.path.expanduser("~/.openclaw-manager")
            os.makedirs(tray_dir, exist_ok=True)
            tray_exe_path = os.path.join(tray_dir, "OpenClaw-Tray.exe")

            # 从服务器下载托盘 exe
            self._update_progress(82, "正在下载托盘管理程序...")
            try:
                urllib.request.urlretrieve(TRAY_EXE_URL, tray_exe_path)
                file_size = os.path.getsize(tray_exe_path)
                if file_size < 1024 * 100:
                    return {"success": True, "message": "托盘程序下载跳过（服务器暂未部署）"}
            except Exception as e:
                # 下载失败不阻塞安装，托盘程序是可选的
                return {"success": True, "message": f"托盘程序下载跳过: {str(e)}"}

            # 复制图标文件
            if hasattr(sys, '_MEIPASS'):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(__file__))

            for icon_name in ['icon.ico', 'icon.png']:
                for search_dir in [os.path.join(base_dir, 'assets'),
                                   os.path.join(base_dir, '..', 'assets')]:
                    icon_src = os.path.join(search_dir, icon_name)
                    if os.path.exists(icon_src):
                        import shutil
                        shutil.copy2(icon_src, os.path.join(tray_dir, icon_name))
                        break

            # 部署完成后立即启动托盘程序
            try:
                os.startfile(tray_exe_path)
            except Exception as e:
                try:
                    import subprocess
                    subprocess.Popen(
                        f'powershell -Command "Start-Process \'{tray_exe_path}\'"',
                        shell=True
                    )
                except Exception as e2:
                    print(f"启动托盘失败: {e}, {e2}")

            return {"success": True, "message": "托盘程序已部署并启动"}
        except Exception as e:
            return {"success": True, "message": f"托盘程序部署跳过: {str(e)}"}

    def _show_retry(self, error_msg):
        """显示重试按钮"""
        tk.Button(
            self.main_frame, text="重试", font=("微软雅黑", 11),
            width=15, command=self.show_install_progress,
            bg="#FF9800", fg="white", relief=tk.FLAT
        ).pack(pady=5)

    # ==================== 第6页：隐私协议 ====================

    def show_privacy_agreement(self):
        self.clear_frame()
        self.add_title("隐私政策")
        self.add_subtitle("请仔细阅读并同意以下隐私政策条款")

        agreement_text = """一、信息收集范围与定义

本政策所称"个人信息"，是指以电子或者其他方式记录的与已识别或者可识别的自然人有关的各种信息，不包括匿名化处理后的信息；"敏感个人信息"是指一旦泄露或者非法使用，容易导致自然人人格尊严受侵害或人身、财产安全受危害的信息，包括但不限于生物识别、宗教信仰、特定身份、医疗健康、金融账户、行踪轨迹、通讯录、通话记录等。本章节所述信息，均为非隐私、非敏感的匿名化数据，不包含任何可识别您个人身份的隐私内容。

二、我们收集的非隐私信息

为向您提供应用搜索、下载、安装、更新、卸载、安全检测及服务优化等基础功能，我们会在您使用本软件过程中，自动收集以下非隐私、非敏感信息：

设备基础信息：设备型号、操作系统版本、CPU架构、屏幕分辨率、设备标识符（如OAID、Android ID，已进行去标识化处理，无法关联个人）、网络类型（WiFi/移动数据）、IP地址（仅用于地域适配与安全风控，不用于精准定位）、WLAN状态信息（仅本地缓存，不上传隐私内容）；

应用相关信息：设备已安装应用列表（仅记录应用包名、版本号、签名信息，不收集应用内数据如文档、照片、聊天记录）、应用安装/卸载/更新时间记录、应用下载来源、安装包MD5/SHA256校验值；

使用行为数据：应用内浏览页面、搜索关键词、下载点击、安装操作、停留时长、交互日志（所有数据均匿名化处理，不关联个人账号或身份）；

系统状态信息：设备存储容量、内存占用、网络连接状态、应用崩溃日志、异常报错信息（仅用于故障排查与稳定性修复）。

特别承诺：我们绝不收集您的姓名、手机号、身份证号、通讯录、短信、通话记录、照片、视频、位置信息、支付账户、生物特征（指纹/人脸）等任何隐私敏感信息，上述收集的信息均无法用于识别您的个人身份。

三、信息收集与使用目的

我们收集上述非隐私信息，仅用于以下合法、必要、最小范围的目的，绝不用于其他未经授权的用途：

保障应用安装、更新、卸载等基础服务正常运行，确保应用与您的设备系统兼容；

对安装包进行安全检测与恶意软件扫描，防范病毒、木马等风险，保护您的设备安全；

优化网络适配、缓存策略、安装流程，提升服务速度与稳定性；

开展匿名化、聚合化的统计分析（如应用下载量、热门排行、用户行为趋势），用于产品功能迭代与服务改进，所有统计结果均为群体数据，不指向任何个人；

遵守国家法律法规、监管要求及司法机关的强制性规定，在法定情形下提供匿名化数据。

四、信息共享、转让与披露规则

内部使用原则：收集的非隐私信息仅在本软件内部使用，不向任何第三方共享、转让、出售您的个人隐私信息；

第三方委托处理：仅为实现基础服务（如应用分发、安全检测），会委托具备合规资质的合作伙伴处理匿名化数据，并签订严格的数据保护协议，明确其仅按本政策目的使用数据，不得泄露、滥用；

法定披露情形：仅在以下情形下，可能向第三方披露匿名化、去标识化的非隐私数据（不包含任何可识别个人的信息）：
（1）遵守法律法规、监管部门的强制性要求；
（2）响应司法机关、行政机关的合法命令；
（3）应对突发公共安全事件，保护您或他人的生命、财产安全。

五、信息存储、安全与期限

存储地点：所有收集的信息存储于中华人民共和国境内，严格遵守国家数据安全与个人信息保护法规；

安全保障：采用加密传输、加密存储、访问权限控制、安全审计、数据脱敏等技术与管理措施，防止数据泄露、篡改、丢失、滥用；

存储期限：仅在实现本政策所述目的的最短必要期限内存储，到期后将进行匿名化删除或不可逆聚合处理，不再保留可关联的原始数据。

六、您的权利

您对非隐私信息的收集与使用享有以下权利：

知情权：可随时通过本软件"设置 - 关于 - 隐私政策"查看完整条款；

控制权：可通过设备系统"设置 - 应用权限"关闭非必要数据收集权限（关闭后不影响应用安装、更新等基础功能）；

更正/删除权：可通过客服渠道申请更正或删除您的非隐私数据（法定留存情形除外）；

投诉与反馈：如对数据处理有异议，可发送邮件至 [客服邮箱] 或拨打 [客服电话]，我们将在15个工作日内完成核查并反馈处理结果。

七、合规声明

本软件严格遵循《中华人民共和国个人信息保护法》《中华人民共和国网络安全法》《常见类型移动互联网应用程序必要个人信息范围规定》等法律法规，坚持合法、正当、最小必要、公开透明原则处理信息。我们再次郑重承诺：本软件仅收集实现基础服务所必需的非隐私、非敏感信息，绝不收集、使用、共享您的任何隐私敏感信息，所有数据处理均以保障服务、保护安全为唯一目的。
"""

        # 使用滚动条的文本框显示长文本
        text_frame = tk.Frame(self.main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, height=15, width=60,
                              font=("微软雅黑", 9), wrap=tk.WORD, bg="#FAFAFA",
                              yscrollcommand=scrollbar.set)
        text_widget.insert(tk.END, agreement_text)
        text_widget.config(state="disabled")
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=text_widget.yview)

        self.agree_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.main_frame, text="我已阅读并同意上述隐私条款",
            variable=self.agree_var, font=("微软雅黑", 10)
        ).pack(pady=10)

        tk.Button(
            self.main_frame, text="完成安装", font=("微软雅黑", 12),
            width=20, height=2, command=self.finish_installation,
            bg="#4CAF50", fg="white", relief=tk.FLAT
        ).pack(pady=10)

    def finish_installation(self):
        if not self.agree_var.get():
            messagebox.showwarning("提示", "请勾选同意隐私条款")
            return

        # 保存用户同意状态
        config_dir = os.path.expanduser("~/.openclaw-manager")
        os.makedirs(config_dir, exist_ok=True)
        import json
        config = {
            "activation_code": self.activation_code,
            "provider": self.selected_provider,
            "model": self.selected_model,
        }
        with open(os.path.join(config_dir, "config.json"), 'w') as f:
            json.dump(config, f, indent=2)

        self.show_complete()

    # ==================== 第7页：完成 ====================

    def show_complete(self):
        self.clear_frame()
        self.add_title("🎉 安装完成！")
        self.add_subtitle("OpenClaw 已成功安装并配置完毕")

        info = [
            "✓ OpenClaw 已安装并配置完成",
            "✓ Gateway 守护服务已启动",
            "✓ 崩溃自动恢复已开启",
            "✓ 开机自启已设置",
            f"✓ 模型: {self.selected_model}",
        ]
        for item in info:
            tk.Label(self.main_frame, text=item, font=("微软雅黑", 10),
                     fg="#4CAF50", anchor="w").pack(fill=tk.X, pady=2)

        tk.Frame(self.main_frame).pack(pady=10)

        tk.Label(self.main_frame,
                 text="Web 界面地址: http://127.0.0.1:18789",
                 font=("Consolas", 11), fg="#2196F3").pack()

        btn_frame = tk.Frame(self.main_frame)
        btn_frame.pack(pady=20)

        tk.Button(
            btn_frame, text="打开 OpenClaw", font=("微软雅黑", 12),
            width=18, height=2, command=lambda: open_browser(),
            bg="#4CAF50", fg="white", relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame, text="退出安装器", font=("微软雅黑", 12),
            width=12, height=2, command=self.root.quit,
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=10)

    def run(self):
        self.root.mainloop()


# ==================== 入口 ====================

def main():
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
