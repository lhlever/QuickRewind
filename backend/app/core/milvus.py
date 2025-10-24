from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from typing import List, Dict, Any, Optional
import numpy as np
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MilvusManager:
    """Milvus向量数据库管理器"""
    
    def __init__(self):
        self.collection = None
        self.is_connected = False
    
    def connect(self):
        """连接到Milvus服务器"""
        if not self.is_connected:
            try:
                connections.connect(
                    host=settings.milvus_host,
                    port=settings.milvus_port,
                    timeout=30
                )
                self.is_connected = True
                logger.info(f"成功连接到Milvus服务器: {settings.milvus_host}:{settings.milvus_port}")
                
                # 确保集合存在
                self._ensure_collection_exists()
                
            except Exception as e:
                logger.error(f"连接Milvus服务器失败: {str(e)}")
                raise
    
    def disconnect(self):
        """断开Milvus连接"""
        if self.is_connected:
            try:
                connections.disconnect()
                self.is_connected = False
                self.collection = None
                logger.info("已断开Milvus连接")
            except Exception as e:
                logger.error(f"断开Milvus连接失败: {str(e)}")
    
    def _ensure_collection_exists(self):
        """确保集合存在，如果不存在则创建"""
        if not utility.has_collection(settings.milvus_collection_name):
            logger.info(f"创建Milvus集合: {settings.milvus_collection_name}")
            
            # 定义字段
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="video_id", dtype=DataType.VARCHAR, max_length=64, description="视频ID"),
                FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32, description="内容类型"),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=512, description="文本内容"),
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
            self.collection = Collection(
                name=settings.milvus_collection_name,
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 128}
            }
            
            self.collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            
            logger.info(f"Milvus集合 {settings.milvus_collection_name} 创建完成")
        else:
            self.collection = Collection(settings.milvus_collection_name)
            logger.info(f"已加载Milvus集合: {settings.milvus_collection_name}")
    
    def insert_vectors(self, vectors: List[np.ndarray], metadata: List[Dict[str, Any]]) -> List[int]:
        """插入向量数据
        
        Args:
            vectors: 向量列表
            metadata: 元数据列表，每个元数据包含video_id, content_type, content等字段
            
        Returns:
            插入的ID列表
        """
        if not self.is_connected:
            self.connect()
        
        # 准备数据
        entities = {
            "video_id": [m["video_id"] for m in metadata],
            "content_type": [m.get("content_type", "transcript") for m in metadata],
            "content": [m["content"] for m in metadata],
            "start_time": [m.get("start_time", 0.0) for m in metadata],
            "end_time": [m.get("end_time", 0.0) for m in metadata],
            "vector": vectors
        }
        
        # 插入数据
        try:
            result = self.collection.insert([entities[field] for field in self.collection.schema.field_names if field != "id"])
            self.collection.flush()
            logger.info(f"成功插入 {len(vectors)} 个向量")
            return result.primary_keys.tolist()
        except Exception as e:
            logger.error(f"插入向量失败: {str(e)}")
            raise
    
    def search_vectors(self, query_vector: np.ndarray, top_k: int = 5, 
                      filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self.is_connected:
            self.connect()
        
        # 加载集合
        self.collection.load()
        
        # 设置搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        # 构建表达式
        expr = None
        if filters:
            conditions = []
            if "video_id" in filters:
                conditions.append(f"video_id == '{filters['video_id']}'")
            if "content_type" in filters:
                conditions.append(f"content_type == '{filters['content_type']}'")
            if "start_time" in filters and "end_time" in filters:
                conditions.append(f"start_time >= {filters['start_time']} && end_time <= {filters['end_time']}")
            
            if conditions:
                expr = " && ".join(conditions)
        
        # 执行搜索
        try:
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["video_id", "content_type", "content", "start_time", "end_time"]
            )
            
            # 处理结果
            search_results = []
            for hit in results[0]:
                search_results.append({
                    "id": hit.id,
                    "distance": hit.distance,
                    "video_id": hit.entity.get("video_id"),
                    "content_type": hit.entity.get("content_type"),
                    "content": hit.entity.get("content"),
                    "start_time": hit.entity.get("start_time"),
                    "end_time": hit.entity.get("end_time")
                })
            
            logger.info(f"搜索完成，返回 {len(search_results)} 个结果")
            return search_results
        except Exception as e:
            logger.error(f"搜索向量失败: {str(e)}")
            raise
    
    def delete_by_video_id(self, video_id: str) -> int:
        """根据视频ID删除向量
        
        Args:
            video_id: 视频ID
            
        Returns:
            删除的数量
        """
        if not self.is_connected:
            self.connect()
        
        try:
            expr = f"video_id == '{video_id}'"
            result = self.collection.delete(expr)
            self.collection.flush()
            deleted_count = result.delete_count
            logger.info(f"已删除视频 {video_id} 的 {deleted_count} 个向量")
            return deleted_count
        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        if not self.is_connected:
            self.connect()
        
        try:
            stats = {
                "collection_name": settings.milvus_collection_name,
                "row_count": self.collection.num_entities,
                "indexes": utility.indexes(settings.milvus_collection_name)
            }
            return stats
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {str(e)}")
            raise


# 创建全局Milvus管理器实例
milvus_manager = MilvusManager()


# 上下文管理器，用于自动连接和断开Milvus
class milvus_context:
    """Milvus上下文管理器"""
    
    def __init__(self, manager: MilvusManager = milvus_manager):
        self.manager = manager
    
    def __enter__(self):
        self.manager.connect()
        return self.manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.disconnect()