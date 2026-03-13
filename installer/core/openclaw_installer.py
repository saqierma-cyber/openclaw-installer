"""
OpenClaw 安装器 & 配置写入器
负责: npm install openclaw → 配置写入(CLI方式) → PM2 守护 → 启动
"""

import subprocess
import platform
import os
import json
import shutil


def _run_cmd(cmd, shell=False, timeout=300, **kwargs):
    """运行命令（修复 Windows 中文编码问题）"""
    extra = {}
    if platform.system() == "Windows":
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=timeout, shell=shell,
        encoding="utf-8", errors="replace",
        **extra, **kwargs
    )


def check_openclaw_installed() -> dict:
    """检查 OpenClaw 是否已安装"""
    oc = "openclaw.cmd" if platform.system() == "Windows" else "openclaw"
    try:
        result = _run_cmd([oc, "--version"])
        if result.returncode == 0:
            return {"installed": True, "version": result.stdout.strip()}
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return {"installed": False, "version": ""}


def _setup_npm_for_china(progress_callback=None):
    """
    国内网络优化：设置 npm 镜像源 + GitHub 加速
    所有 GitHub 访问（SSH 和 HTTPS）统一走 ghproxy 代理
    """
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    git_cmd = "git"

    if progress_callback:
        progress_callback("正在配置国内网络优化...")

    # 1. 设置 npm 淘宝镜像源
    _run_cmd([npm_cmd, "config", "set", "registry", "https://registry.npmmirror.com"], timeout=15)

    # 2. 清除可能冲突的旧 git 配置
    _run_cmd([git_cmd, "config", "--global", "--unset-all", "url.https://github.com/.insteadOf"], timeout=10)

    # 3. 所有 GitHub 访问统一走 ghproxy（SSH 和 HTTPS 都直接指向 ghproxy）
    _run_cmd([git_cmd, "config", "--global",
              "url.https://ghproxy.net/https://github.com/.insteadOf", "https://github.com/"], timeout=15)
    _run_cmd([git_cmd, "config", "--global",
              "url.https://ghproxy.net/https://github.com/.insteadOf", "git@github.com:"], timeout=15)
    _run_cmd([git_cmd, "config", "--global",
              "url.https://ghproxy.net/https://github.com/.insteadOf", "ssh://git@github.com/"], timeout=15)


def install_openclaw(progress_callback=None) -> dict:
    """
    安装 OpenClaw
    从自有服务器下载完整安装包（含所有依赖），直接解压到 npm 全局目录
    不需要 npm install，不需要连接 GitHub
    """
    import urllib.request
    import tempfile
    import tarfile

    OPENCLAW_TGZ_URL = os.environ.get("OPENCLAW_TGZ_URL", "http://localhost:8000/static/openclaw-full-2026.3.2.tgz")

    try:
        # 先检查是否已经安装
        check = check_openclaw_installed()
        if check["installed"]:
            return {
                "success": True,
                "message": f"OpenClaw {check['version']} 已安装，跳过安装步骤"
            }

        # ===== 第1步：确定 npm 全局目录 =====
        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        result = _run_cmd([npm_cmd, "root", "-g"], timeout=15)
        if result and result.returncode == 0:
            npm_global_dir = result.stdout.strip()
        else:
            # Windows 默认路径
            npm_global_dir = os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules")

        if not os.path.exists(npm_global_dir):
            os.makedirs(npm_global_dir, exist_ok=True)

        # ===== 第2步：下载完整安装包 =====
        if progress_callback:
            progress_callback("正在从服务器下载 OpenClaw 安装包（约 480MB，请耐心等待）...")

        temp_dir = tempfile.mkdtemp()
        tgz_path = os.path.join(temp_dir, "openclaw-full.tgz")

        def download_progress(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                downloaded_mb = block_num * block_size / 1024 / 1024
                total_mb = total_size / 1024 / 1024
                percent = min(100, int(downloaded_mb / total_mb * 100))
                progress_callback(f"正在下载... {downloaded_mb:.0f}/{total_mb:.0f} MB ({percent}%)")

        urllib.request.urlretrieve(OPENCLAW_TGZ_URL, tgz_path, reporthook=download_progress)

        file_size = os.path.getsize(tgz_path)
        if file_size < 10 * 1024 * 1024:  # 小于 10MB 说明下载不完整
            return {"success": False, "message": f"下载异常：文件仅 {file_size // 1024 // 1024}MB，应约 480MB"}

        # ===== 第3步：解压到 npm 全局目录 =====
        if progress_callback:
            progress_callback("正在解压安装（可能需要 1-2 分钟）...")

        with tarfile.open(tgz_path, 'r:gz') as tar:
            tar.extractall(path=npm_global_dir)

        # ===== 第4步：创建命令行链接（Windows 上需要 .cmd 文件）=====
        if progress_callback:
            progress_callback("正在配置命令行工具...")

        _create_openclaw_cmd_link(npm_global_dir)

        # ===== 第5步：补全 Windows 平台 native binding =====
        # tgz 在 Linux 打包，缺少 Windows native addon（如 @snazzah/davey-win32-x64-msvc）
        # 用 npm install 在 openclaw 目录内补装，npm 会自动拉取当前平台的 optional deps
        if platform.system() == "Windows":
            if progress_callback:
                progress_callback("正在安装 Windows 平台组件...")
            openclaw_pkg_dir = os.path.join(npm_global_dir, "openclaw")
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
            _run_cmd([npm_cmd, "install", "--ignore-scripts=false"],
                     timeout=120, cwd=openclaw_pkg_dir)

        # 清理临时文件
        try:
            os.remove(tgz_path)
            os.rmdir(temp_dir)
        except Exception:
            pass

        # 验证安装
        check = check_openclaw_installed()
        if check["installed"]:
            return {"success": True, "message": f"OpenClaw {check['version']} 安装成功"}
        else:
            return {"success": True, "message": "解压完成，但命令验证失败，可能需要重启终端"}

    except subprocess.TimeoutExpired:
        return {"success": False, "message": "安装超时，请检查网络后重试"}
    except FileNotFoundError:
        return {"success": False, "message": "未找到 npm 命令，请确保 Node.js 已正确安装"}
    except Exception as e:
        return {"success": False, "message": f"安装出错: {str(e)}"}


def write_config_via_cli(
    provider_key: str,
    model_name: str,
    api_key: str,
    base_url: str = None,
    progress_callback=None
) -> dict:
    """
    直接写入 OpenClaw 配置文件，模拟 `openclaw configure --section model` 向导的结果
    不再依赖 CLI 命令，直接操作 JSON 配置文件
    """
    try:
        if progress_callback:
            progress_callback("正在写入模型配置...")

        return _write_config_directly(provider_key, model_name, api_key, base_url)

    except Exception as e:
        return {"success": False, "message": f"配置写入失败: {str(e)}"}


# ==================== 品牌 → OpenClaw provider 映射 ====================
# type: "builtin" = 内置提供商（只需 .env + agents.defaults，不写 models.providers）
# type: "custom"  = 自定义提供商（需要完整 models.providers 配置）
PROVIDER_CONFIG_MAP = {
    # ===== 内置提供商（不需要 models.providers）=====
    "openai": {
        "type": "builtin",
        "provider": "openai",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-5.1-codex",
        "model_name": "GPT-5.1 Codex",
        "need_url": False,
    },
    "anthropic": {
        "type": "builtin",
        "provider": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-6",
        "model_name": "Claude Sonnet 4.6",
        "need_url": False,
    },
    "google": {
        "type": "builtin",
        "provider": "google",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-3-pro-preview",
        "model_name": "Gemini 3 Pro",
        "need_url": False,
    },
    "openrouter": {
        "type": "builtin",
        "provider": "openrouter",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "anthropic/claude-sonnet-4-5",
        "model_name": "Claude Sonnet 4.5 (via OpenRouter)",
        "need_url": False,
    },
    "xai": {
        "type": "builtin",
        "provider": "xai",
        "env_key": "XAI_API_KEY",
        "default_model": "grok-3",
        "model_name": "Grok 3",
        "need_url": False,
    },
    "mistral": {
        "type": "builtin",
        "provider": "mistral",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-large-latest",
        "model_name": "Mistral Large",
        "need_url": False,
    },
    "groq": {
        "type": "builtin",
        "provider": "groq",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.1-70b-versatile",
        "model_name": "Llama 3.1 70B",
        "need_url": False,
    },
    "zai": {
        "type": "builtin",
        "provider": "zai",
        "env_key": "ZAI_API_KEY",
        "default_model": "glm-5",
        "model_name": "GLM-5",
        "need_url": False,
    },
    "volcengine": {
        "type": "builtin",
        "provider": "volcengine",
        "env_key": "VOLCANO_ENGINE_API_KEY",
        "default_model": "doubao-seed-1-8-251228",
        "model_name": "豆包 Seed 1.8",
        "need_url": False,
    },
    "byteplus": {
        "type": "builtin",
        "provider": "byteplus",
        "env_key": "BYTEPLUS_API_KEY",
        "default_model": "seed-1-8-251228",
        "model_name": "Seed 1.8 (BytePlus)",
        "need_url": False,
    },
    "opencode": {
        "type": "builtin",
        "provider": "opencode",
        "env_key": "OPENCODE_API_KEY",
        "default_model": "claude-opus-4-6",
        "model_name": "Claude Opus 4.6 (via OpenCode)",
        "need_url": False,
    },
    "kilocode": {
        "type": "builtin",
        "provider": "kilocode",
        "env_key": "KILOCODE_API_KEY",
        "default_model": "anthropic/claude-opus-4.6",
        "model_name": "Claude Opus 4.6 (via Kilo)",
        "need_url": False,
    },
    "huggingface": {
        "type": "builtin",
        "provider": "huggingface",
        "env_key": "HF_TOKEN",
        "default_model": "deepseek-ai/DeepSeek-R1",
        "model_name": "DeepSeek R1",
        "need_url": False,
    },

    # ===== 自定义提供商（需要 models.providers）=====
    "moonshot": {
        "type": "custom",
        "provider": "moonshot",
        "env_key": "MOONSHOT_API_KEY",
        "default_model": "kimi-k2.5",
        "model_name": "Kimi K2.5",
        "base_url": "https://api.moonshot.ai/v1",
        "api": "openai-completions",
        "need_url": True,
        "models": [
            {"id": "kimi-k2.5", "name": "Kimi K2.5"},
            {"id": "kimi-k2-thinking", "name": "Kimi K2 Thinking"},
        ],
    },
    "kimi-coding": {
        "type": "builtin",
        "provider": "kimi-coding",
        "env_key": "KIMI_API_KEY",
        "default_model": "k2p5",
        "model_name": "Kimi Coding K2.5",
        "base_url": "",
        "api": "anthropic-messages",
        "need_url": False,
        "models": [{"id": "k2p5", "name": "Kimi Coding K2.5"}],
    },
    "minimax": {
        "type": "custom",
        "provider": "minimax",
        "env_key": "MINIMAX_API_KEY",
        "default_model": "MiniMax-M2.5",
        "model_name": "MiniMax M2.5",
        "base_url": "",
        "api": "anthropic-messages",
        "need_url": True,
        "models": [{"id": "MiniMax-M2.5", "name": "MiniMax M2.5"}],
    },
    "ollama": {
        "type": "custom",
        "provider": "ollama",
        "env_key": "",
        "default_model": "llama3.3",
        "model_name": "Llama 3.3 (本地)",
        "base_url": "http://127.0.0.1:11434/v1",
        "api": "openai-completions",
        "need_url": False,
        "models": [{"id": "llama3.3", "name": "Llama 3.3"}],
    },
    "synthetic": {
        "type": "custom",
        "provider": "synthetic",
        "env_key": "SYNTHETIC_API_KEY",
        "default_model": "hf:MiniMaxAI/MiniMax-M2.5",
        "model_name": "MiniMax M2.5 (Synthetic)",
        "base_url": "https://api.synthetic.new/anthropic",
        "api": "anthropic-messages",
        "need_url": False,
        "models": [{"id": "hf:MiniMaxAI/MiniMax-M2.5", "name": "MiniMax M2.5"}],
    },
    "vllm": {
        "type": "custom",
        "provider": "vllm",
        "env_key": "VLLM_API_KEY",
        "default_model": "your-model",
        "model_name": "vLLM (自托管)",
        "base_url": "http://127.0.0.1:8000/v1",
        "api": "openai-completions",
        "need_url": True,
        "models": [],
    },

    # ===== 自定义 URL（用户完全自定义）=====
    "custom": {
        "type": "custom",
        "provider": "custom",
        "env_key": "",
        "default_model": "",
        "model_name": "",
        "base_url": "",
        "api": "openai-completions",
        "need_url": True,
        "models": [],
    },
}


def _write_config_directly(
    provider_key: str,
    model_name: str,
    api_key: str,
    base_url: str = None
) -> dict:
    """
    直接写配置文件，根据提供商类型走不同逻辑：
    - builtin（内置提供商）：只写 .env + agents.defaults，不写 models.providers
    - custom（自定义提供商）：写完整 models.providers 配置
    """
    try:
        config_dir = os.path.expanduser("~/.openclaw")
        config_file = os.path.join(config_dir, "openclaw.json")
        os.makedirs(config_dir, exist_ok=True)

        # 确保 sessions 目录存在（否则 doctor 会报错）
        sessions_dir = os.path.join(config_dir, "agents", "main", "sessions")
        os.makedirs(sessions_dir, exist_ok=True)

        # 读取现有配置或创建新的
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError:
                    config = {}

        # 获取 provider 配置映射
        pconfig = PROVIDER_CONFIG_MAP.get(provider_key, {})
        provider_type = pconfig.get("type", "custom")
        oc_provider = pconfig.get("provider", provider_key)
        env_key_name = pconfig.get("env_key", "")
        default_model = pconfig.get("default_model", model_name)

        # 如果用户指定了模型名，优先用用户的
        if model_name and model_name != default_model:
            default_model = model_name

        full_model = f"{oc_provider}/{default_model}"

        # ===== 删除旧格式 =====
        config.pop("agent", None)

        # ===== 写入 meta =====
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        config["meta"] = {
            "lastTouchedVersion": "2026.3.2",
            "lastTouchedAt": now_iso
        }

        # ===== 写入 wizard 标记 =====
        config["wizard"] = {
            "lastRunAt": now_iso,
            "lastRunVersion": "2026.3.2",
            "lastRunCommand": "configure",
            "lastRunMode": "local"
        }

        # ===== 写入 auth profiles =====
        profile_key = f"{oc_provider}:default"
        config["auth"] = {
            "profiles": {
                profile_key: {
                    "provider": oc_provider,
                    "mode": "api_key"
                }
            }
        }

        # ===== 写入 agents 配置 =====
        config["agents"] = {
            "defaults": {
                "model": {
                    "primary": full_model,
                    "fallbacks": []
                }
            }
        }

        # ===== 写入 gateway 配置 =====
        existing_token = config.get("gateway", {}).get("auth", {}).get("token", "")
        config["gateway"] = {
            "mode": "local",
            "auth": {
                "mode": "none",
                "token": existing_token or _generate_random_token()
            }
        }

        # ===== 根据提供商类型分别处理 models 配置 =====
        if provider_type == "builtin":
            # 内置提供商：不写 models.providers，删除可能存在的旧配置
            config.pop("models", None)
            # 内置提供商必须将 API Key 写入 openclaw.json 的 env 字段
            # OpenClaw 通过 env 字段加载内置提供商的密钥（与 .env 文件不同）
            if env_key_name and api_key:
                config["env"] = config.get("env", {})
                config["env"][env_key_name] = api_key

        elif provider_type == "custom":
            # 自定义提供商：写完整 models.providers
            actual_url = base_url or pconfig.get("base_url", "")
            api_format = pconfig.get("api", "openai-completions")
            models_list = pconfig.get("models", [])
            if not models_list:
                models_list = [{"id": default_model, "name": model_name or default_model}]

            provider_config = {
                "api": api_format,
                "models": models_list,
            }
            if actual_url:
                provider_config["baseUrl"] = actual_url
            if api_key and env_key_name:
                provider_config["apiKey"] = f"${{{env_key_name}}}"

            config["models"] = {
                "mode": "merge",
                "providers": {oc_provider: provider_config}
            }

        # ===== 写入配置文件 =====
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # ===== 写入 API Key 到 credentials 和 .env =====
        _write_api_key_credential(config_dir, oc_provider, api_key, env_key_name)

        return {"success": True, "message": f"配置写入成功（模型: {full_model}）"}

    except Exception as e:
        return {"success": False, "message": f"配置写入失败: {str(e)}"}


def _generate_random_token() -> str:
    """生成随机 gateway token"""
    import secrets
    return secrets.token_hex(24)


def _write_api_key_credential(config_dir: str, provider: str, api_key: str, env_key_name: str = ""):
    """
    将 API Key 写入 OpenClaw 的 credentials 存储和 .env 文件
    """
    if not api_key:
        return

    # 写入 provider 的 credential 文件
    creds_dir = os.path.join(config_dir, "credentials")
    os.makedirs(creds_dir, exist_ok=True)

    cred_file = os.path.join(creds_dir, f"{provider}.json")
    cred_data = {
        "provider": provider,
        "mode": "api_key",
        "apiKey": api_key
    }

    with open(cred_file, 'w', encoding='utf-8') as f:
        json.dump(cred_data, f, indent=2)

    # 写入 .env 环境变量（内置提供商必须靠这个读取 Key）
    if not env_key_name:
        # 从 PROVIDER_CONFIG_MAP 动态获取
        for pconfig in PROVIDER_CONFIG_MAP.values():
            if pconfig.get("provider") == provider:
                env_key_name = pconfig.get("env_key", "")
                break
        if not env_key_name:
            env_key_name = f"{provider.upper().replace('-', '_')}_API_KEY"

    env_file = os.path.join(config_dir, ".env")
    env_lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_lines = f.readlines()

    _update_env_line(env_lines, env_key_name, api_key)

    with open(env_file, 'w') as f:
        f.writelines(env_lines)


def _update_env_line(lines: list, key: str, value: str):
    """更新 .env 文件中的某一行"""
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")


def _create_openclaw_cmd_link(npm_global_dir: str):
    """
    在 npm 全局 bin 目录创建 openclaw.cmd 链接
    解压方式安装不会自动创建 .cmd 文件，需要手动创建
    """
    if platform.system() != "Windows":
        return

    # npm 全局 bin 目录（.cmd 文件所在位置）
    # npm_global_dir 是 node_modules 目录，bin 目录在它的上一级
    bin_dir = os.path.dirname(npm_global_dir)
    openclaw_entry = os.path.join(npm_global_dir, "openclaw", "openclaw.mjs")

    if not os.path.exists(openclaw_entry):
        # 尝试其他可能的入口文件
        for entry in ["openclaw.mjs", "dist/cli.js", "bin/openclaw.js"]:
            candidate = os.path.join(npm_global_dir, "openclaw", entry)
            if os.path.exists(candidate):
                openclaw_entry = candidate
                break

    # 创建 openclaw.cmd
    cmd_path = os.path.join(bin_dir, "openclaw.cmd")
    if not os.path.exists(cmd_path):
        cmd_content = f'@echo off\nnode "{openclaw_entry}" %*\n'
        with open(cmd_path, 'w') as f:
            f.write(cmd_content)

    # 同时创建一个 PowerShell 脚本版本
    ps1_path = os.path.join(bin_dir, "openclaw.ps1")
    if not os.path.exists(ps1_path):
        ps1_content = f'#!/usr/bin/env pwsh\nnode "{openclaw_entry}" $args\n'
        with open(ps1_path, 'w') as f:
            f.write(ps1_content)


def _get_pm2_cmd() -> str:
    """获取 PM2 命令（Windows 上需要用 pm2.cmd）"""
    return "pm2.cmd" if platform.system() == "Windows" else "pm2"


def _get_openclaw_cmd() -> str:
    """获取 openclaw 命令（Windows 上需要用 openclaw.cmd）"""
    return "openclaw.cmd" if platform.system() == "Windows" else "openclaw"


def install_pm2(progress_callback=None) -> dict:
    """安装 PM2 进程管理器"""
    try:
        if progress_callback:
            progress_callback("正在安装 PM2 进程管理器...")

        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        result = _run_cmd([npm_cmd, "install", "-g", "pm2"], timeout=120)

        if result.returncode == 0:
            return {"success": True, "message": "PM2 安装成功"}
        else:
            return {"success": False, "message": f"PM2 安装失败: {result.stderr[:300]}"}

    except Exception as e:
        return {"success": False, "message": f"PM2 安装出错: {str(e)}"}


def setup_guardian_service(progress_callback=None) -> dict:
    """
    设置守护服务（方案一：不依赖 Python 环境）
    
    架构:
    - PM2 直接托管 openclaw gateway（只依赖 Node.js）
    - 托盘 exe 开机自启，内部线程负责监控 + 崩溃重启通知 + 数据采集
    """
    try:
        if progress_callback:
            progress_callback("正在配置 Gateway 守护服务...")

        pm2 = _get_pm2_cmd()
        oc = _get_openclaw_cmd()

        # 先停止可能存在的旧实例（忽略错误）
        _run_cmd([pm2, "delete", "openclaw-gateway"], timeout=30)

        # PM2 必须启动 .mjs 入口文件（不能传 .cmd，否则 Node 把批处理当 JS 解析报 SyntaxError）
        npm_global = os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules")
        openclaw_mjs = os.path.join(npm_global, "openclaw", "openclaw.mjs")
        if not os.path.exists(openclaw_mjs):
            # 尝试其他入口
            for entry in ["dist/cli.js", "bin/openclaw.js"]:
                candidate = os.path.join(npm_global, "openclaw", entry)
                if os.path.exists(candidate):
                    openclaw_mjs = candidate
                    break

        result = _run_cmd([
            pm2, "start", openclaw_mjs,
            "--name", "openclaw-gateway",
            "--interpreter", "node",
            "--", "gateway", "--port", "18789"
        ], timeout=30)

        # 设置 PM2 开机自启
        _run_cmd([pm2, "startup"], timeout=30)
        _run_cmd([pm2, "save"], timeout=30)

        # 注册托盘 exe 开机自启
        _register_tray_autostart()

        return {"success": True, "message": "守护服务配置成功"}

    except Exception as e:
        return {"success": False, "message": f"守护服务配置失败: {str(e)}"}


def _register_tray_autostart():
    """
    注册托盘管理程序开机自启
    方式：在 Windows 启动文件夹中创建快捷方式
    """
    if platform.system() != "Windows":
        return

    try:
        import winreg

        # 获取托盘 exe 路径
        tray_exe = _get_tray_exe_path()
        if not tray_exe or not os.path.exists(tray_exe):
            print(f"[WARNING] 托盘 exe 未找到: {tray_exe}，跳过开机自启注册")
            return

        # 方式1：通过注册表添加开机自启
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "OpenClawManager", 0, winreg.REG_SZ, f'"{tray_exe}"')
        winreg.CloseKey(key)

    except Exception as e:
        # 方式2：回退到启动文件夹创建 bat 文件
        try:
            startup_dir = os.path.join(
                os.environ.get("APPDATA", ""),
                r"Microsoft\Windows\Start Menu\Programs\Startup"
            )
            if os.path.exists(startup_dir):
                bat_path = os.path.join(startup_dir, "OpenClawManager.bat")
                tray_exe = _get_tray_exe_path()
                with open(bat_path, 'w') as f:
                    f.write(f'@echo off\nstart "" "{tray_exe}"\n')
        except Exception:
            pass


def _get_tray_exe_path() -> str:
    """获取托盘 exe 的路径"""
    # 打包后的 exe 会在安装目录
    manager_dir = os.path.expanduser("~/.openclaw-manager")

    # 优先查找打包的 exe
    exe_path = os.path.join(manager_dir, "OpenClaw-Tray.exe")
    if os.path.exists(exe_path):
        return exe_path

    # 开发模式：返回 python 脚本路径
    script_path = os.path.join(manager_dir, "main.py")
    if os.path.exists(script_path):
        return script_path

    return exe_path  # 返回预期路径，安装时会复制过去


def start_gateway(progress_callback=None) -> dict:
    """
    启动 Gateway
    用完整路径通过 PowerShell Start-Process 启动
    """
    import time as time_module
    import urllib.request

    try:
        if progress_callback:
            progress_callback("正在启动 OpenClaw Gateway...")

        # 直接构建完整路径（不依赖 shutil.which，因为刚安装的 .cmd 可能还没被缓存）
        if platform.system() == "Windows":
            oc_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "openclaw.cmd")
            if not os.path.exists(oc_path):
                oc_path = shutil.which("openclaw.cmd") or shutil.which("openclaw") or ""
            if not oc_path or not os.path.exists(oc_path):
                return {"success": False, "message": f"找不到 openclaw.cmd"}

            # 用 PowerShell Start-Process 启动，窗口最小化
            subprocess.Popen(
                ["powershell", "-Command",
                 f'Start-Process -FilePath "{oc_path}" -ArgumentList "gateway","--port","18789" -WindowStyle Minimized'],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            oc_path = shutil.which("openclaw") or "openclaw"
            subprocess.Popen(
                [oc_path, "gateway", "--port", "18789"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        # 等待 Gateway 真正就绪（最多等 30 秒）
        if progress_callback:
            progress_callback("等待 Gateway 启动完成...")

        for i in range(15):
            time_module.sleep(2)
            try:
                req = urllib.request.urlopen("http://127.0.0.1:18789/", timeout=3)
                if progress_callback:
                    progress_callback("Gateway 已就绪！")
                return {"success": True, "message": "Gateway 启动成功"}
            except Exception:
                pass

            if progress_callback:
                progress_callback(f"等待 Gateway 启动完成...（{(i+1)*2}秒）")

        return {"success": True, "message": "Gateway 启动中，请稍等几秒再刷新浏览器"}

    except Exception as e:
        return {"success": False, "message": f"启动失败: {str(e)}"}


def open_browser():
    """打开浏览器访问 OpenClaw Web UI"""
    import webbrowser
    webbrowser.open("http://127.0.0.1:18789")
