from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建JWT访问令牌
    
    Args:
        subject: 令牌主题，通常是用户ID或用户名
        expires_delta: 令牌过期时间增量，默认为配置中的过期时间
        
    Returns:
        JWT令牌字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """
    验证JWT令牌
    
    Args:
        token: JWT令牌字符串
        
    Returns:
        如果验证成功，返回用户名；否则返回None
    """
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    验证密码（简化版，直接比较明文）
    
    Args:
        plain_password: 明文密码
        stored_password: 存储的密码
        
    Returns:
        如果密码匹配，返回True；否则返回False
    """
    return plain_password == stored_password

def get_password_hash(password: str) -> str:
    """
    获取密码（简化版，直接返回明文）
    
    Args:
        password: 明文密码
        
    Returns:
        密码本身（不加密）
    """
    return password