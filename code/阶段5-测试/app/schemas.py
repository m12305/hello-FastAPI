"""
schemas.py — Pydantic 数据校验模型（被测试的目标应用）

关键原则：
  - 数据库模型 ≠ API 模型 —— 二者完全分离
  - 输入的密码是明文（UserCreate.password）
  - 输出的密码绝不能出现（UserResponse 没有 password 字段）
  - ConfigDict(from_attributes=True) 支持 ORM 对象直接转为 Pydantic
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ═══════════════════════════════════════════
# 用户
# ═══════════════════════════════════════════

class UserCreate(BaseModel):
    """注册请求体 —— 密码是明文输入"""
    username: str = Field(
        min_length=3, max_length=50,
        description="用户名，3-50 字符",
        examples=["zhangsan"]
    )
    email: EmailStr = Field(
        description="邮箱地址",
        examples=["zhang@example.com"]
    )
    password: str = Field(
        min_length=6, max_length=100,
        description="密码，6-100 字符",
        examples=["12345678"]
    )


class UserResponse(BaseModel):
    """
    用户信息响应 —— 绝不包含 password / hashed_password！
    使用 from_attributes=True 可直接从 ORM 对象转换。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """更新用户信息"""
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None


class UserRoleUpdate(BaseModel):
    """修改角色（仅管理员可用）"""
    role: str = Field(pattern="^(user|editor|admin)$")


# ═══════════════════════════════════════════
# 文章
# ═══════════════════════════════════════════

class PostCreate(BaseModel):
    """创建文章 —— 不包含 user_id，由后端从 Token 中获取"""
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)


class PostUpdate(BaseModel):
    """更新文章 —— 所有字段可选"""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=5000)


class PostResponse(BaseModel):
    """文章响应 —— 包含作者信息"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    user_id: int
    author_username: str = ""
    created_at: datetime


# ═══════════════════════════════════════════
# 认证
# ═══════════════════════════════════════════

class Token(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """登录请求体（用于测试时的 JSON 登录）"""
    username: str
    password: str
