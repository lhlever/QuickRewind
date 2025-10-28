from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()


class VideoStatus(str, enum.Enum):
    """视频处理状态枚举"""
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(Base):
    """视频模型"""
    __tablename__ = "videos"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    filesize = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.UPLOADING)
    
    # 处理结果路径
    audio_path = Column(String, nullable=True)
    subtitle_path = Column(String, nullable=True)
    transcript_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    # 元数据
    video_metadata = Column(JSON, nullable=True)
    
    # 注意：处理步骤信息现在在内存中跟踪，不存储到数据库
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Video(id={self.id}, filename={self.filename}, status={self.status})>"