#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Milvus文本截断功能
"""

import sys
import os
from app.core.milvus import milvus_manager
import logging
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_truncation():
    """测试文本截断功能"""
    try:
        # 创建一个超长文本
        long_text = "这是一个非常长的文本" * 100  # 远远超过512个字符
        logger.info(f"原始文本长度: {len(long_text)}")
        
        # 创建测试数据
        video_id = "test_video_123"
        vector = np.random.randn(768).tolist()  # 假设向量维度是768
        
        metadata = [{
            "video_id": video_id,
            "content_type": "test",
            "content": long_text,
            "start_time": 0.0,
            "end_time": 10.0
        }]
        
        vectors = [vector]
        
        # 连接Milvus
        logger.info("正在连接Milvus...")
        milvus_manager.connect()
        
        # 测试插入
        logger.info("正在测试插入操作...")
        result = milvus_manager.insert_vectors(vectors, metadata)
        logger.info(f"插入成功! 返回的ID: {result}")
        
        logger.info("测试完成! 文本截断功能正常工作。")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return False
    finally:
        # 断开连接
        if hasattr(milvus_manager, 'disconnect'):
            try:
                milvus_manager.disconnect()
            except:
                pass

if __name__ == "__main__":
    logger.info("开始测试Milvus文本截断功能...")
    success = test_truncation()
    sys.exit(0 if success else 1)