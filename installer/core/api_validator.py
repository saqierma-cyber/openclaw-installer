"""
API Key 验证器
根据提供商类型（builtin/custom）走不同验证逻辑
内置提供商使用官方默认 URL 验证，自定义提供商由用户输入 URL
"""

import requests
import json

# ==================== 大模型品牌列表 ====================
# 与 openclaw_installer.py 的 PROVIDER_CONFIG_MAP 对齐
# need_url: 是否需要用户手动输入 API URL
# type: builtin（内置）/ custom（自定义）
MODEL_PROVIDERS = {
    # ===== 内置提供商 =====
    "openai":       {"name": "OpenAI (GPT)", "default_model": "gpt-5.1-codex", "type": "builtin", "need_url": False},
    "anthropic":    {"name": "Anthropic (Claude)", "default_model": "claude-sonnet-4-6", "type": "builtin", "need_url": False},
    "google":       {"name": "Google (Gemini)", "default_model": "gemini-3-pro-preview", "type": "builtin", "need_url": False},
    "openrouter":   {"name": "OpenRouter", "default_model": "anthropic/claude-sonnet-4-5", "type": "builtin", "need_url": False},
    "xai":          {"name": "xAI (Grok)", "default_model": "grok-3", "type": "builtin", "need_url": False},
    "mistral":      {"name": "Mistral", "default_model": "mistral-large-latest", "type": "builtin", "need_url": False},
    "groq":         {"name": "Groq", "default_model": "llama-3.1-70b-versatile", "type": "builtin", "need_url": False},
    "zai":          {"name": "Z.AI (GLM)", "default_model": "glm-5", "type": "builtin", "need_url": False},
    "volcengine":   {"name": "火山引擎 (豆包)", "default_model": "doubao-seed-1-8-251228", "type": "builtin", "need_url": False},
    "byteplus":     {"name": "BytePlus", "default_model": "seed-1-8-251228", "type": "builtin", "need_url": False},
    "opencode":     {"name": "OpenCode Zen", "default_model": "claude-opus-4-6", "type": "builtin", "need_url": False},
    "kilocode":     {"name": "Kilocode", "default_model": "anthropic/claude-opus-4.6", "type": "builtin", "need_url": False},
    "huggingface":  {"name": "Hugging Face", "default_model": "deepseek-ai/DeepSeek-R1", "type": "builtin", "need_url": False},
    # ===== 自定义提供商 =====
    "kimi-coding":  {"name": "Kimi Coding", "default_model": "k2p5", "type": "custom", "need_url": False},
    "moonshot":     {"name": "Moonshot (Kimi)", "default_model": "kimi-k2.5", "type": "custom", "need_url": True},
    "minimax":      {"name": "MiniMax", "default_model": "MiniMax-M2.5", "type": "custom", "need_url": True},
    "ollama":       {"name": "Ollama (本地模型)", "default_model": "llama3.3", "type": "custom", "need_url": False},
    "synthetic":    {"name": "Synthetic", "default_model": "hf:MiniMaxAI/MiniMax-M2.5", "type": "custom", "need_url": False},
    "vllm":         {"name": "vLLM (自托管)", "default_model": "your-model", "type": "custom", "need_url": True},
    # ===== 完全自定义 =====
    "custom":       {"name": "自定义 / 其他", "default_model": "", "type": "custom", "need_url": True},
}

# 内置提供商的默认验证 URL
_BUILTIN_VALIDATE_URLS = {
    "openai":       "https://api.openai.com/v1",
    "anthropic":    "https://api.anthropic.com/v1",
    "google":       "https://generativelanguage.googleapis.com/v1beta",
    "openrouter":   "https://openrouter.ai/api/v1",
    "xai":          "https://api.x.ai/v1",
    "mistral":      "https://api.mistral.ai/v1",
    "groq":         "https://api.groq.com/openai/v1",
    "zai":          "https://open.bigmodel.cn/api/paas/v4",
    "volcengine":   "https://ark.cn-beijing.volces.com/api/v3",
    "byteplus":     "https://ark.byteplussea.com/api/v3",
    "opencode":     "https://opencode.ai/api/v1",
    "kilocode":     "https://api.kilocode.ai/v1",
    "huggingface":  "https://router.huggingface.co/v1",
}


def get_provider_list() -> list[dict]:
    """获取品牌列表（用于 GUI 下拉框）"""
    providers = []
    for key, info in MODEL_PROVIDERS.items():
        providers.append({
            "key": key,
            "name": info["name"],
            "need_url": info.get("need_url", False),
            "type": info.get("type", "custom"),
            "is_custom": key == "custom",
        })
    # 排序：内置提供商 > 自定义提供商 > custom
    def sort_key(x):
        if x["is_custom"]:
            return (2, x["name"])
        elif x["type"] == "builtin":
            return (0, x["name"])
        else:
            return (1, x["name"])
    providers.sort(key=sort_key)
    return providers


def get_default_model(provider_key: str) -> str:
    """获取某品牌的默认模型"""
    provider = MODEL_PROVIDERS.get(provider_key)
    if provider:
        return provider.get("default_model", "")
    return ""


def get_provider_info(provider_key: str) -> dict:
    """获取提供商完整信息（供 GUI 使用）"""
    return MODEL_PROVIDERS.get(provider_key, {})


def get_endpoints(provider_key: str) -> list[str]:
    """兼容旧代码：返回一个默认的 endpoint 名"""
    return ["默认"]


def get_endpoint_config(provider_key: str, endpoint_name: str) -> dict | None:
    """兼容旧代码：返回简化的 config"""
    provider = MODEL_PROVIDERS.get(provider_key)
    if not provider:
        return None
    return {
        "base_url": "",
        "models": [provider.get("default_model", "")] if provider.get("default_model") else [],
        "default_model": provider.get("default_model", ""),
    }


def validate_api_key(
    provider_key: str,
    endpoint_name: str,
    api_key: str,
    model: str = None,
    custom_url: str = None
) -> dict:
    """
    验证 API Key 是否有效

    验证逻辑：
    - 内置提供商（need_url=False）：使用官方默认 URL 验证，不需要用户输入 URL
    - 自定义提供商（need_url=True）：使用用户输入的 URL 验证
    - Ollama 等无需 Key 的提供商：跳过验证直接通过

    状态码判断（宽容策略）：
    - 200: Key 有效 → 通过
    - 400/403: Key 能被识别 → 视为通过
    - 429: 额度不足 → 视为通过（提示充值）
    - 401: Key 无效 → 失败
    - 404: URL 错误 → 失败
    """
    provider_info = MODEL_PROVIDERS.get(provider_key, {})
    provider_type = provider_info.get("type", "custom")
    need_url = provider_info.get("need_url", True)

    # Ollama 等无需 API Key 的本地提供商，直接通过
    if provider_key == "ollama":
        return {"valid": True, "status_code": 0, "message": "本地模型无需验证 API Key", "detail": ""}

    if not api_key:
        return {"valid": False, "status_code": 0, "message": "请输入 API Key", "detail": ""}

    # 确定验证用的 base_url
    if need_url:
        # 自定义提供商：必须由用户提供 URL
        if not custom_url:
            return {"valid": False, "status_code": 0, "message": "请输入 API URL", "detail": ""}
        base_url = custom_url.rstrip('/')
    else:
        # 内置提供商 或 有默认 URL 的自定义提供商
        if custom_url:
            base_url = custom_url.rstrip('/')
        else:
            base_url = _BUILTIN_VALIDATE_URLS.get(provider_key, "")
            if not base_url:
                # 对于 kimi-coding、synthetic 等有默认配置的，跳过验证
                return {"valid": True, "status_code": 0, "message": "API Key 已保存（跳过在线验证）", "detail": ""}

    # 确定模型
    if not model:
        model = get_default_model(provider_key) or "test"

    # 使用 anthropic-messages 格式的提供商（需要 /messages 端点 + x-api-key）
    _ANTHROPIC_MSG_PROVIDERS = {"kimi-coding", "minimax", "synthetic"}

    # 构建验证请求的 URL 和 Headers
    if provider_key == "anthropic" or provider_key in _ANTHROPIC_MSG_PROVIDERS:
        # Anthropic 格式（含 minimax、kimi-coding、synthetic 等）
        test_url = f"{base_url}/messages" if "/v1" in base_url else f"{base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    elif provider_key == "google":
        # Google Gemini 使用不同的认证方式
        test_url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
    else:
        # OpenAI 兼容格式（大多数提供商）
        test_url = f"{base_url}/chat/completions" if "/v1" in base_url else f"{base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    # 请求体
    body = {
        "model": model,
        "max_tokens": 5,
        "messages": [{"role": "user", "content": "hi"}]
    }

    try:
        response = requests.post(
            test_url,
            headers=headers,
            json=body,
            timeout=30,
        )

        status = response.status_code
        resp_text = response.text[:300]

        if status == 200:
            return {"valid": True, "status_code": 200, "message": "API Key 验证通过，连接正常", "detail": ""}
        elif status == 401:
            return {"valid": False, "status_code": 401, "message": "API Key 不正确，请检查后重新输入", "detail": resp_text}
        elif status == 403:
            return {"valid": True, "status_code": 403, "message": "API Key 有效（权限受限，但 Key 已验证通过）", "detail": resp_text}
        elif status == 400:
            return {"valid": True, "status_code": 400, "message": "API Key 有效（请求格式需适配，但 Key 已验证通过）", "detail": resp_text}
        elif status == 429:
            return {"valid": True, "status_code": 429, "message": "API Key 有效，但额度不足或请求过快，建议充值后使用", "detail": resp_text}
        elif status == 404:
            return {"valid": False, "status_code": 404, "message": "API 路径不正确，请检查 URL（尝试加或去掉 /v1）", "detail": resp_text}
        else:
            return {"valid": False, "status_code": status, "message": f"API 返回异常 (HTTP {status})", "detail": resp_text}

    except requests.ConnectionError:
        return {"valid": False, "status_code": 0, "message": "无法连接到 API 服务器，请检查网络", "detail": ""}
    except requests.Timeout:
        return {"valid": False, "status_code": 0, "message": "连接超时，请检查网络或 URL", "detail": ""}
    except Exception as e:
        return {"valid": False, "status_code": 0, "message": f"验证失败: {str(e)}", "detail": ""}
