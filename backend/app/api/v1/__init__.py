from fastapi import APIRouter
from .video_routes import router as video_router

# 创建v1版本API路由器
api_v1_router = APIRouter()

# 包含视频相关路由
api_v1_router.include_router(video_router)