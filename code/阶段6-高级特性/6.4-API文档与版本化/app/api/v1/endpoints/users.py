"""
V1 用户端点 —— 旧版 API

V1 特点：
  - 注册只需 username + email + password
  - 响应字段简单：只有 id, username, email
  - 内容少但稳定
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()

# ── 模拟数据库 ──
fake_users_db: list[dict] = []


# ── V1 Schema ──
class UserCreateV1(BaseModel):
    """V1 注册请求：只有基础字段"""
    username: str = Field(min_length=3, max_length=50, examples=["zhangsan"])
    email: EmailStr = Field(examples=["zhang@example.com"])
    password: str = Field(min_length=6, max_length=100, examples=["12345678"])


class UserResponseV1(BaseModel):
    """V1 用户响应：3 个基础字段"""
    id: int
    username: str
    email: str


# ── V1 端点 ──
@router.post("/register", response_model=UserResponseV1, status_code=201)
def register_v1(data: UserCreateV1):
    """
    V1 注册 —— 基础字段。

    只需 username + email + password。
    """
    # 重复检查
    for u in fake_users_db:
        if u["username"] == data.username:
            raise HTTPException(400, "用户名已存在")

    user = {
        "id": len(fake_users_db) + 1,
        "username": data.username,
        "email": data.email,
        "password": data.password,  # V1 明文存密码（错误示范！）
    }
    fake_users_db.append(user)
    return UserResponseV1(id=user["id"], username=user["username"], email=user["email"])


@router.get("/users", response_model=list[UserResponseV1])
def list_users_v1():
    """
    V1 用户列表 —— 返回基础字段。

    注意：V1 没有分页，也没有 role 字段。
    """
    return [
        UserResponseV1(id=u["id"], username=u["username"], email=u["email"])
        for u in fake_users_db
    ]


@router.get("/users/{user_id}", response_model=UserResponseV1)
def get_user_v1(user_id: int):
    """V1 用户详情"""
    for u in fake_users_db:
        if u["id"] == user_id:
            return UserResponseV1(id=u["id"], username=u["username"], email=u["email"])
    raise HTTPException(404, "用户不存在")
