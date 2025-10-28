"""
数据库重置脚本
用于删除并重新创建所有数据库表
"""
import logging
from app.core.database import engine, Base, drop_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """重置数据库：删除所有表并重新创建"""
    try:
        logger.info("开始重置数据库...")
        
        # 删除所有表
        logger.info("正在删除所有表...")
        drop_db()
        
        # 创建所有表
        logger.info("正在重新创建所有表...")
        init_db()
        
        logger.info("数据库重置成功！")
        print("✅ 数据库重置成功！所有表已重新创建，processing_steps字段已添加")
        
    except Exception as e:
        logger.error(f"数据库重置失败：{str(e)}")
        print(f"❌ 数据库重置失败：{str(e)}")
        raise

if __name__ == "__main__":
    reset_database()