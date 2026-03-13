"""
激活码验证器（客户端）
联网到验证服务器校验激活码
"""

import requests
import hashlib
import hmac
import time as time_module
import json
import sys
import os

from core.fingerprint import generate_fingerprint

SERVER_URL = os.environ.get("OPENCLAW_SERVER_URL", "http://localhost:8000")

# 与服务端相同的密钥
SECRET_KEY = os.environ.get("OPENCLAW_SECRET_KEY", "CHANGE_ME")


def _generate_signature(payload: dict) -> tuple[str, int]:
    """生成请求签名"""
    timestamp = int(time_module.time())
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    message = f"{payload_str}|{timestamp}|{SECRET_KEY}"

    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature, timestamp


def verify_activation_code(code: str) -> dict:
    """
    验证激活码
    返回: {"status": "success/invalid/expired/used/error", "message": "..."}
    """
    try:
        fingerprint = generate_fingerprint()
        payload = {"code": code, "fingerprint": fingerprint}
        signature, timestamp = _generate_signature(payload)

        response = requests.post(
            f"{SERVER_URL}/api/v1/activate",
            json={
                "code": code,
                "fingerprint": fingerprint,
                "signature": signature,
                "timestamp": timestamp,
            },
            timeout=15,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "message": f"服务器返回错误 ({response.status_code})"
            }

    except requests.ConnectionError:
        return {"status": "error", "message": "无法连接到验证服务器，请检查网络"}
    except requests.Timeout:
        return {"status": "error", "message": "连接超时，请稍后重试"}
    except Exception as e:
        return {"status": "error", "message": f"验证失败: {str(e)}"}
