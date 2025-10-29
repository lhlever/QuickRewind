from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from app.api import api_router
from app.core.config import settings
from app.core.database import engine, Base

# 配置日志
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title="QuickRewind API",
    description="视频内容分析和智能检索后端服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加GZip中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由
app.include_router(api_router)

# 创建数据库表
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Starting up QuickRewind API...")
    
    # 可以在这里初始化其他服务或进行系统检查
    try:
        # 验证数据库连接
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
        
        # 验证Redis连接（如果需要）
        if settings.redis_enabled:
            from app.core.redis import redis_client
            await redis_client.ping()
            logger.info("Redis connection established")
            await redis_client.close()
        
        # 初始化MCP工具注册表
        from app.core.tool_registry import initialize as initialize_tool_registry
        initialize_tool_registry()
        logger.info("MCP tool registry initialized")
        
    except Exception as e:
        logger.error(f"Startup check failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down QuickRewind API...")
    
    # 关闭数据库连接（添加安全检查）
    if engine is not None:
        try:
            await engine.dispose()
            logger.info("Database connection disposed")
        except Exception as e:
            logger.error(f"Error disposing database connection: {str(e)}")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to QuickRewind API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "QuickRewind API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )