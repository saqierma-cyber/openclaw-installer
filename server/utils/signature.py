"""
请求签名工具
客户端和服务端共用签名/验签逻辑，防止伪造请求
"""

import hashlib
import os
import hmac
import time
import json

# !!!! 部署前必须修改此密钥 !!!!
SECRET_KEY = os.environ.get("OPENCLAW_SECRET_KEY", "CHANGE_ME")


def generate_signature(payload: dict, timestamp: int = None) -> tuple[str, int]:
    """
    生成请求签名
    返回: (signature, timestamp)
    """
    if timestamp is None:
        timestamp = int(time.time())

    # 将 payload 序列化为稳定的字符串
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    message = f"{payload_str}|{timestamp}|{SECRET_KEY}"

    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature, timestamp


def verify_signature(payload: dict, signature: str, timestamp: int,
                     max_age_seconds: int = 600) -> bool:
    """
    验证请求签名
    max_age_seconds: 签名有效期（默认10分钟，防重放攻击，同时容忍时钟偏差）
    """
    # 检查时间戳是否过期
    current_time = int(time.time())
    if abs(current_time - timestamp) > max_age_seconds:
        return False

    # 重新计算签名
    expected_signature, _ = generate_signature(payload, timestamp)
    return hmac.compare_digest(signature, expected_signature)
