#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建Milvus集合以应用新的schema配置
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymilvus import connections, utility
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
        
        logger.info("Milvus集合重建完成！现在可以重新启动应用程序，它将使用新的schema创建集合。")
        logger.info("新的配置：content字段最大长度已从512增加到2048")
        
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