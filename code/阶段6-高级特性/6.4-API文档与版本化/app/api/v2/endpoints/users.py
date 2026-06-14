"""
V2 用户端点 —— 新版 API

V2 改进：
  1. 注册增加 phone 字段（手机号）
  2. 响应增加 role + created_at 字段
  3. 用户列表支持分页（page + size）
  4. bcrypt 密码哈希（不能明文存）
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()

# ── 模拟数据库 ──
fake_users_db_v2: list[dict] = []


# ── V2 Schema（字段更多、更丰富）──
class UserCreateV2(BaseModel):
    """V2 注册请求：增加了手机号"""
    username: str = Field(min_length=3, max_length=50, examples=["zhangsan"])
    email: EmailStr = Field(examples=["zhang@example.com"])
    password: str = Field(min_length=6, max_length=100, examples=["12345678"])
    phone: str = Field(
        pattern=r"^1[3-9]\d{9}$",
        description="中国大陆手机号",
        examples=["13800138000"],
    )


class UserResponseV2(BaseModel):
    """V2 用户响应：增加了 role + created_at"""
    id: int
    username: str
    email: str
    phone: str
    role: str
    created_at: str


class PaginatedResponse(BaseModel):
    """V2 统一分页格式"""
    data: list[UserResponseV2]
    page: int
    size: int
    total: int


# ── V2 端点 ──
@router.post("/register", response_model=UserResponseV2, status_code=201)
def register_v2(data: UserCreateV2):
    """
    V2 注册 —— 增加了手机号字段。

    相比 V1 改进：
      - 手机号格式校验
      - bcrypt 密码哈希（生产环境）
      - 自动分配 role
    """
    for u in fake_users_db_v2:
        if u["username"] == data.username:
            raise HTTPException(400, "用户名已存在")
        if u["phone"] == data.phone:
            raise HTTPException(400, "手机号已被注册")

    user = {
        "id": len(fake_users_db_v2) + 1,
        "username": data.username,
        "email": data.email,
        "phone": data.phone,
        "password": f"<bcrypt:{data.password}>",  # V2 用哈希存储
        "role": "user",
        "created_at": datetime.now().isoformat(),
    }
    fake_users_db_v2.append(user)
    return _to_response(user)


@router.get("/users", response_model=PaginatedResponse)
def list_users_v2(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """
    V2 用户列表 —— 支持分页 + 返回更丰富的字段。

    相比 V1 改进：
      - 分页（page + size）
      - 返回 phone、role、created_at
    """
    start = (page - 1) * size
    end = start + size
    paginated = fake_users_db_v2[start:end]
    return PaginatedResponse(
        data=[_to_response(u) for u in paginated],
        page=page,
        size=size,
        total=len(fake_users_db_v2),
    )


@router.get("/users/{user_id}", response_model=UserResponseV2)
def get_user_v2(user_id: int):
    """
    V2 用户详情 —— 比 V1 多了 phone、role、created_at。
    """
    for u in fake_users_db_v2:
        if u["id"] == user_id:
            return _to_response(u)
    raise HTTPException(404, "用户不存在")


# ── 辅助函数 ──
def _to_response(user: dict) -> UserResponseV2:
    return UserResponseV2(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        phone=user["phone"],
        role=user["role"],
        created_at=user["created_at"],
    )
