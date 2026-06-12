"""
schemas.py — Pydantic 模型：认证与授权的数据契约

关键原则（同阶段 3）：
  - 数据库模型 ≠ API 模型
  - UserResponse 绝不包含 hashed_password
  - UserCreate 的 password 是明文输入
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ═══════════════════════════════════════════
# 用户
# ═══════════════════════════════════════════

class UserCreate(BaseModel):
    """注册请求体"""
    username: str = Field(min_length=3, max_length=50, examples=["zhangsan"])
    email: EmailStr = Field(examples=["zhang@example.com"])
    password: str = Field(min_length=6, max_length=100, examples=["12345678"])


class UserResponse(BaseModel):
    """用户信息响应——绝不包含密码！"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    """修改角色请求体（仅 admin 可用）"""
    role: str = Field(pattern="^(user|editor|admin)$", examples=["editor"])


# ═══════════════════════════════════════════
# Token
# ═══════════════════════════════════════════

class Token(BaseModel):
    """登录/刷新后返回的 Token 对"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """刷新 Token 的请求体"""
    refresh_token: str


# ═══════════════════════════════════════════
# 文章（演示数据所有权）
# ═══════════════════════════════════════════

class PostCreate(BaseModel):
    """创建文章"""
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)


class PostUpdate(BaseModel):
    """更新文章"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=5000)


class PostResponse(BaseModel):
    """文章响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    user_id: int
    created_at: datetime
