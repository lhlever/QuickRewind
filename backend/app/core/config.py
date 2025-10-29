from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
import os
import json
from pathlib import Path


class Settings(BaseSettings):
    """应用配置管理"""
    # 应用基础配置
    app_name: str = "QuickRewind"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: List[str] = ["*"]
    
    # 安全配置
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 火山引擎配置（简化版）
    volcengine_api_key: str = "your-volcengine-api-key"
    volcengine_region: str = "https://ark.cn-beijing.volces.com/api/v3"
    volcengine_model: str = "kimi-k2-250905"
    volcengine_embedding_model: str = "text-embedding-v1"
    volcengine_embedding_dim: int = 2560
    
    # Milvus配置
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection_name: str = "video_content_vectors"
    milvus_dim: int = 2560
    
    # Redis配置
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    
    # 数据库配置
    database_url: str = "postgresql://admin:admin@localhost:5432/mydb"
    
    # 路径配置
    data_dir: str = "/app/data"
    video_dir: str = "/app/data/videos"
    audio_dir: str = "/app/data/audio"
    subtitle_dir: str = "/app/data/subtitles"
    vector_dir: str = "/app/data/vectors"
    log_dir: str = "/app/logs"
    
    # 处理配置
    max_video_size: int = 1073741824  # 1GB
    workers: int = 4
    batch_size: int = 300
    
    # 语音识别配置
    speech_engine: str = "funasr"  # whisper 或 funasr
    
    # FunASR配置
    funasr_model_name: str = "paraformer-zh"
    funasr_vad_model: str = "fsmn-vad"
    funasr_punc_model: str = "ct-punc"
    
    # Whisper配置
    whisper_model: str = "small"  # tiny, base, small, medium, large
    whisper_language: str = "zh"
    whisper_device: str = "cpu"
    
    # Celery配置
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "Asia/Shanghai"
    celery_enable_utc: bool = True
    
    # 移除可能导致问题的validator
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        # 移除可能导致问题的环境变量值
        env_kwargs = kwargs.copy()
        if 'celery_accept_content' in env_kwargs:
            del env_kwargs['celery_accept_content']
        
        # 使用清理后的参数初始化
        super().__init__(**env_kwargs)
        
        # 强制设置celery_accept_content的值
        self.celery_accept_content = ["json"]
        
        # 开发环境使用相对路径
        if self.debug:
            base_dir = Path(__file__).resolve().parent.parent.parent
            
            # 更新路径配置为相对路径
            self.data_dir = str(base_dir / "data")
            self.video_dir = str(base_dir / "data" / "videos")
            self.audio_dir = str(base_dir / "data" / "audio")
            self.subtitle_dir = str(base_dir / "data" / "subtitles")
            self.vector_dir = str(base_dir / "data" / "vectors")
            self.log_dir = str(base_dir / "logs")
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.data_dir,
            self.video_dir,
            self.audio_dir,
            self.subtitle_dir,
            self.vector_dir,
            self.log_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# 创建全局配置实例
settings = Settings()