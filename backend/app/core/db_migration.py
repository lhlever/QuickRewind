"""
数据库迁移脚本
用于更新已存在的数据库表结构
"""
import logging
from sqlalchemy import text
from app.core.database import engine

logger = logging.getLogger(__name__)

def run_migrations():
    """运行数据库迁移"""
    try:
        with engine.connect() as conn:
            # 检查videos表是否有processing_steps字段
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='videos' AND column_name='processing_steps'
            """)
            result = conn.execute(check_column_query).fetchone()
            
            if not result:
                # 添加processing_steps字段
                add_column_query = text("""
                    ALTER TABLE videos 
                    ADD COLUMN processing_steps JSONB
                """)
                conn.execute(add_column_query)
                conn.commit()
                logger.info("成功添加processing_steps字段到videos表")
                print("数据库迁移成功：已添加processing_steps字段")
            else:
                logger.info("processing_steps字段已存在，无需迁移")
                print("数据库迁移：processing_steps字段已存在")
    except Exception as e:
        logger.error(f"数据库迁移失败：{str(e)}")
        print(f"数据库迁移失败：{str(e)}")
        raise

if __name__ == "__main__":
    run_migrations()