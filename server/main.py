"""
OpenClaw 安装工具 - 验证服务器
FastAPI 后端，提供激活码验证接口
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.activation import router as activation_router
from models.database import init_db

app = FastAPI(
    title="OpenClaw Installer 验证服务器",
    version="1.0.0",
    description="激活码验证服务"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activation_router, prefix="/api/v1", tags=["激活码"])


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "openclaw-installer-server"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
