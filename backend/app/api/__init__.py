from fastapi import APIRouter
from .v1 import api_v1_router

# 创建主API路由器
api_router = APIRouter()

# 包含v1版本API
api_router.include_router(api_v1_router)