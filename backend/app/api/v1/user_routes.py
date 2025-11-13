from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.auth import get_current_admin_user, get_current_active_user
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate, UserCreate

# 创建路由器
router = APIRouter(prefix="/users", tags=["用户管理"])

@router.get("/", response_model=List[UserSchema])
async def get_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    search: Optional[str] = Query(None, description="搜索关键词（用户名或邮箱）"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    is_superuser: Optional[bool] = Query(None, description="是否为管理员"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取用户列表（仅管理员）
    
    Args:
        skip: 跳过的记录数
        limit: 返回的记录数
        search: 搜索关键词
        is_active: 是否激活
        is_superuser: 是否为管理员
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        用户列表
    """
    query = db.query(User)
    
    # 搜索过滤
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    # 状态过滤
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
        
    if is_superuser is not None:
        query = query.filter(User.is_superuser == is_superuser)
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    获取指定用户信息（仅管理员）
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        用户信息
        
    Raises:
        HTTPException: 如果用户不存在
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    更新用户信息（仅管理员）
    
    Args:
        user_id: 用户ID
        user_update: 更新数据
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        更新后的用户信息
        
    Raises:
        HTTPException: 如果用户不存在或邮箱/用户名已存在
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查用户名是否已存在（如果要更新的用户名与当前用户不同）
    if user_update.username and user_update.username != db_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
    
    # 检查邮箱是否已存在（如果要更新的邮箱与当前用户不同）
    if user_update.email and user_update.email != db_user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )
    
    # 更新用户信息
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    删除用户（仅管理员）
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 如果用户不存在或尝试删除自己
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    db.delete(db_user)
    db.commit()
    return {"message": "用户已删除"}

@router.post("/", response_model=UserSchema)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    创建用户（仅管理员）
    
    Args:
        user_data: 用户数据
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        创建的用户信息
        
    Raises:
        HTTPException: 如果用户名或邮箱已存在
    """
    # 检查用户名是否已存在
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建新用户
    from app.core.security import get_password_hash
    
    password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password=password,
        full_name=user_data.full_name,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/{user_id}/status")
async def toggle_user_status(
    user_id: str,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    切换用户激活状态（仅管理员）
    
    Args:
        user_id: 用户ID
        is_active: 激活状态
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        更新结果
        
    Raises:
        HTTPException: 如果用户不存在或尝试禁用自己
    """
    if user_id == current_user.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账户"
        )
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    db_user.is_active = is_active
    db.commit()
    return {"message": f"用户已{'激活' if is_active else '禁用'}"}

@router.put("/{user_id}/role")
async def toggle_user_role(
    user_id: str,
    is_superuser: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    切换用户管理员角色（仅管理员）
    
    Args:
        user_id: 用户ID
        is_superuser: 管理员状态
        db: 数据库会话
        current_user: 当前管理员用户
        
    Returns:
        更新结果
        
    Raises:
        HTTPException: 如果用户不存在或尝试取消自己的管理员权限
    """
    if user_id == current_user.id and not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能取消自己的管理员权限"
        )
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    db_user.is_superuser = is_superuser
    db.commit()
    return {"message": f"用户已{'设为' if is_superuser else '取消'}管理员"}