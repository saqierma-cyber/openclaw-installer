"""
激活码验证接口
"""

import time
from fastapi import APIRouter, Request
from pydantic import BaseModel
from models.database import activate_code, log_activation
from utils.signature import verify_signature

router = APIRouter()


class ActivationRequest(BaseModel):
    code: str
    fingerprint: str
    signature: str
    timestamp: int


class ActivationResponse(BaseModel):
    status: str  # success / invalid / expired / used / error
    message: str


@router.post("/activate", response_model=ActivationResponse)
async def activate(req: ActivationRequest, request: Request):
    """激活码验证接口"""
    client_ip = request.client.host if request.client else "unknown"

    # 万能激活码（永久有效，不限设备）
    universal_code = os.environ.get("UNIVERSAL_CODE", "")
    if universal_code and req.code == universal_code:
        log_activation(req.code, "activate_success", req.fingerprint, client_ip,
                       detail="universal code")
        return ActivationResponse(status="success", message="激活成功")

    # 验证签名
    payload = {"code": req.code, "fingerprint": req.fingerprint}
    if not verify_signature(payload, req.signature, req.timestamp):
        time_diff = abs(int(time.time()) - req.timestamp)
        log_activation(req.code, "signature_failed", req.fingerprint, client_ip,
                       detail=f"time_diff={time_diff}s")
        return ActivationResponse(status="error", message="签名验证失败")

    # 执行激活
    result = activate_code(req.code, req.fingerprint)

    # 记录日志
    log_activation(
        code=req.code,
        action=f"activate_{result['status']}",
        fingerprint=req.fingerprint,
        ip_address=client_ip,
        detail=result["message"]
    )

    return ActivationResponse(status=result["status"], message=result["message"])


@router.get("/verify/{code}")
async def verify_code_status(code: str):
    """查询激活码状态（管理用，生产环境建议加鉴权）"""
    from models.database import get_activation_code
    code_info = get_activation_code(code)
    if not code_info:
        return {"status": "not_found"}
    return {
        "code": code_info["code"],
        "status": code_info["status"],
        "created_at": code_info["created_at"],
        "activated_at": code_info["activated_at"],
        "expires_at": code_info["expires_at"]
    }
