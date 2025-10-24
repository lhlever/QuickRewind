import redis
from typing import Optional, Any
from app.core.config import settings
import json
import asyncio
import aioredis


class RedisManager:
    """Redis连接管理器"""
    
    def __init__(self):
        self.redis_client = None
        self.async_redis_client = None
    
    def connect(self):
        """同步连接Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            print("Redis同步连接成功")
        return self.redis_client
    
    async def connect_async(self):
        """异步连接Redis"""
        if not self.async_redis_client:
            self.async_redis_client = await aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            await self.async_redis_client.ping()
            print("Redis异步连接成功")
        return self.async_redis_client
    
    def disconnect(self):
        """断开同步连接"""
        if self.redis_client:
            self.redis_client.close()
            self.redis_client = None
            print("Redis同步连接已断开")
    
    async def disconnect_async(self):
        """断开异步连接"""
        if self.async_redis_client:
            await self.async_redis_client.close()
            self.async_redis_client = None
            print("Redis异步连接已断开")
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置键值对"""
        client = self.connect()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return client.set(key, value, ex=expire)
    
    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        client = self.connect()
        value = client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    def delete(self, key: str) -> int:
        """删除键"""
        client = self.connect()
        return client.delete(key)
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        client = self.connect()
        return client.exists(key) > 0
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        client = self.connect()
        return client.expire(key, seconds)
    
    # 异步方法
    async def set_async(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """异步设置键值对"""
        client = await self.connect_async()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await client.set(key, value, ex=expire)
    
    async def get_async(self, key: str) -> Optional[Any]:
        """异步获取值"""
        client = await self.connect_async()
        value = await client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def delete_async(self, key: str) -> int:
        """异步删除键"""
        client = await self.connect_async()
        return await client.delete(key)
    
    async def exists_async(self, key: str) -> bool:
        """异步检查键是否存在"""
        client = await self.connect_async()
        return await client.exists(key) > 0
    
    async def expire_async(self, key: str, seconds: int) -> bool:
        """异步设置键的过期时间"""
        client = await self.connect_async()
        return await client.expire(key, seconds)


# 创建全局Redis管理器实例
redis_manager = RedisManager()


# 上下文管理器，用于自动连接和断开Redis
class redis_context:
    """Redis同步上下文管理器"""
    
    def __init__(self, manager: RedisManager = redis_manager):
        self.manager = manager
    
    def __enter__(self):
        return self.manager.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.disconnect()


class redis_context_async:
    """Redis异步上下文管理器"""
    
    def __init__(self, manager: RedisManager = redis_manager):
        self.manager = manager
    
    async def __aenter__(self):
        return await self.manager.connect_async()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.manager.disconnect_async()


# 常用的键前缀
class RedisKeys:
    """Redis键前缀定义"""
    VIDEO_STATUS = "video:status:{video_id}"
    VIDEO_PROGRESS = "video:progress:{video_id}"
    TRANSCRIPT_TEXT = "video:transcript:{video_id}"
    SUMMARY = "video:summary:{video_id}"
    USER_SESSION = "user:session:{user_id}"
    API_RATE_LIMIT = "rate_limit:api:{user_id}"
    UPLOAD_TOKEN = "upload:token:{token}"
    CACHED_QUERY = "query:cache:{query_hash}"