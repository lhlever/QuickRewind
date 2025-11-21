"""
应用上下文变量

使用 contextvars 来存储请求级别的上下文信息，如用户ID等。
这些变量在异步操作中是线程安全的。
"""

from contextvars import ContextVar
from typing import Optional

# 存储当前请求的用户ID
current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)


def set_current_user_id(user_id: Optional[str]) -> None:
    """
    设置当前请求的用户ID

    Args:
        user_id: 用户ID
    """
    current_user_id.set(user_id)


def get_current_user_id() -> Optional[str]:
    """
    获取当前请求的用户ID

    Returns:
        用户ID，如果未设置则返回None
    """
    return current_user_id.get()
