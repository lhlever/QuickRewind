from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.models.video import Base


class VectorIndex(Base):
    """向量索引模型"""
    __tablename__ = "vector_indices"
    
    id = Column(String, primary_key=True, autoincrement=False)  # Milvus中的ID
    video_id = Column(String, ForeignKey("videos.id"), nullable=False, index=True)
    
    # 内容信息
    content_type = Column(String, nullable=False)  # "transcript", "summary", "qa"等
    content = Column(Text, nullable=False)  # 原始文本内容
    
    # 时间信息（如果是视频内容）
    start_time = Column(Float, nullable=True)  # 开始时间（秒）
    end_time = Column(Float, nullable=True)  # 结束时间（秒）
    
    # 元数据
    vector_metadata = Column(Text, nullable=True)  # 存储额外的元数据，JSON格式
    
    # 向量维度信息
    vector_dim = Column(Integer, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<VectorIndex(id={self.id}, video_id={self.video_id}, content_type={self.content_type})>"