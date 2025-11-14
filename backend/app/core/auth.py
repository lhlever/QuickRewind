from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User

# HTTP Bearer认证方案
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前用户
    
    Args:
        credentials: HTTP认证凭据
        db: 数据库会话
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 如果认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 验证令牌
    token = credentials.credentials
    username = verify_token(token)
    
    if username is None:
        raise credentials_exception
    
    # 从数据库获取用户
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        当前活跃用户对象
        
    Raises:
        HTTPException: 如果用户已被禁用
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="用户已被禁用"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    获取当前管理员用户
    
    Args:
        current_user: 当前活跃用户
        
    Returns:
        当前管理员用户对象
        
    Raises:
        HTTPException: 如果用户不是管理员
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="权限不足"
        )
    return current_user

def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取可选的当前用户（不强制要求认证）
    
    Args:
        request: FastAPI请求对象
        db: 数据库会话
        
    Returns:
        当前用户对象，如果未认证则返回None
    """
    try:
        # 从请求头中获取Authorization
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
            
        # 解析Bearer令牌
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
            
        token = parts[1]
        username = verify_token(token)
        
        if username is None:
            return None
            
        # 从数据库获取用户
        user = db.query(User).filter(User.username == username).first()
        return user
    except Exception:
        return None