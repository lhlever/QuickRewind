from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, validator


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    is_active: Optional[bool] = Field(True, description="是否激活")


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    is_superuser: Optional[bool] = Field(False, description="是否为管理员")


class UserUpdate(BaseModel):
    """更新用户模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_superuser: Optional[bool] = Field(None, description="是否管理员")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="新密码")


class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: str
    password: str
    is_superuser: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    api_calls: int = 0
    storage_used: int = 0

    model_config = ConfigDict(from_attributes=True)


class User(UserBase):
    """用户响应模型"""
    id: str
    is_superuser: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    api_calls: int = 0
    storage_used: int = 0

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RegisterRequest(UserCreate):
    """注册请求模型"""
    confirm_password: str = Field(..., description="确认密码")

    def validate_passwords_match(self):
        """验证密码是否匹配"""
        if self.password != self.confirm_password:
            raise ValueError("密码不匹配")
        return self


class PasswordChange(BaseModel):
    """修改密码模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")

    def validate_passwords_match(self):
        """验证新密码是否匹配"""
        if self.new_password != self.confirm_password:
            raise ValueError("新密码不匹配")
        return self


