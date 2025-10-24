from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from app.models.video import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    
    # 用户信息
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # 权限控制
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # 元数据
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # API使用统计
    api_calls = Column(Integer, default=0)
    storage_used = Column(Integer, default=0)  # 存储使用量（字节）
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"