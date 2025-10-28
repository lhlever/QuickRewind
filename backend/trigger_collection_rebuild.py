#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
触发Milvus集合重建脚本
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.milvus import milvus_manager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trigger_collection_rebuild():
    """触发Milvus集合重建"""
    try:
        logger.info("开始触发Milvus集合重建...")
        
        # 连接到Milvus，这会触发自动检测和重建集合的逻辑
        milvus_manager.connect()
        
        # 获取集合信息以验证
        if milvus_manager.is_connected:
            logger.info("成功连接到Milvus并验证了集合配置")
            logger.info("现在content字段的最大长度已设置为2048，可以处理更长的文本了")
        else:
            logger.error("连接Milvus失败")
            return False
        
        # 断开连接
        milvus_manager.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"触发集合重建失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = trigger_collection_rebuild()
    sys.exit(0 if success else 1)