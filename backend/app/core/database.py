from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings
from app.models.video import Base

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表"""
    # 导入所有模型，确保它们被注册
    from app.models import Video, User, VectorIndex
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    print("数据库初始化完成")


def drop_db():
    """删除所有表（仅用于开发/测试）"""
    Base.metadata.drop_all(bind=engine)
    print("数据库表已删除")