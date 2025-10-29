#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建Milvus集合以应用新的schema配置
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
from app.core.config import settings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def rebuild_milvus_collection():
    """重建Milvus集合"""
    try:
        # 连接到Milvus
        logger.info(f"正在连接到Milvus服务器: {settings.milvus_host}:{settings.milvus_port}")
        connections.connect(
            host=settings.milvus_host,
            port=settings.milvus_port,
            timeout=30
        )
        
        # 检查集合是否存在
        if utility.has_collection(settings.milvus_collection_name):
            logger.warning(f"集合 {settings.milvus_collection_name} 已存在，正在删除...")
            utility.drop_collection(settings.milvus_collection_name)
            logger.info(f"集合 {settings.milvus_collection_name} 已删除")
        
        # 创建新的集合
        logger.info(f"正在创建新的Milvus集合: {settings.milvus_collection_name}，维度: {settings.milvus_dim}")
        
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=64, description="视频ID"),
            FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32, description="内容类型"),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048, description="文本内容"),
            FieldSchema(name="start_time", dtype=DataType.FLOAT, description="开始时间（秒）"),
            FieldSchema(name="end_time", dtype=DataType.FLOAT, description="结束时间（秒）"),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.milvus_dim, description="向量表示")
        ]
        
        # 创建schema
        schema = CollectionSchema(
            fields=fields,
            description="视频内容向量存储",
            enable_dynamic_field=True
        )
        
        # 创建集合
        collection = Collection(
            name=settings.milvus_collection_name,
            schema=schema
        )
        
        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        
        collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        
        logger.info(f"Milvus集合 {settings.milvus_collection_name} 创建完成！")
        logger.info(f"新的配置：content字段最大长度: 2048, 向量维度: {settings.milvus_dim}")
        
        # 断开连接
        connections.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"重建Milvus集合失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("开始重建Milvus集合...")
    success = rebuild_milvus_collection()
    sys.exit(0 if success else 1)