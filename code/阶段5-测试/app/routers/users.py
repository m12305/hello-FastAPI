"""
app/routers/users.py — 用户与认证路由

包含：
  1. 认证端点：POST /register, POST /login
  2. 用户端点：GET /users, GET /users/{id}, PATCH /users/{id}, DELETE /users/{id}
  3. 管理员端点：GET /admin/users, PATCH /admin/users/{id}/role
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserResponse, UserUpdate, UserRoleUpdate,
    Token, LoginRequest,
)
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_admin,
)

# ── 创建路由器 ──
router = APIRouter(tags=["用户与认证"])


# ═══════════════════════════════════════════════════════════
# 1. 认证端点
# ═══════════════════════════════════════════════════════════

@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册。

    测试要点：
      - 正常注册 → 201
      - 重复用户名 → 400
      - 非法数据（短用户名、空密码等）→ 422
    """
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 创建用户
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录 → 返回 JWT Token。

    测试要点：
      - 正确密码 → 200 + access_token
      - 错误密码 → 401
      - 不存在的用户 → 401
      - 停用用户 → 403
    """
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token)


# ═══════════════════════════════════════════════════════════
# 2. 用户 CRUD 端点
# ═══════════════════════════════════════════════════════════

@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """获取所有用户列表（公开接口）"""
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    获取单个用户。

    测试要点：
      - 存在的 ID → 200
      - 不存在的 ID → 404
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新用户信息 —— 只能更新自己的信息。

    测试要点：
      - 更新自己 → 200
      - 更新别人 → 403（权限不足）
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 所有权检查：只能改自己
    if current_user.id != user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能修改自己的信息")

    if data.username is not None:
        # 检查新用户名是否已被占用
        dup = db.query(User).filter(User.username == data.username, User.id != user_id).first()
        if dup:
            raise HTTPException(status_code=400, detail="用户名已被占用")

        user.username = data.username
    if data.email is not None:
        user.email = data.email

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=200)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除用户 —— 只能删除自己。

    测试要点：
      - 删除自己 → 200
      - 删除别人 → 403
      - 删除后 GET → 404
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if current_user.id != user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能删除自己的账号")

    db.delete(user)
    db.commit()
    return {"message": f"用户 {user.username} 已删除"}


# ═══════════════════════════════════════════════════════════
# 3. 管理员端点（需要 admin 角色）
# ═══════════════════════════════════════════════════════════

@router.get("/admin/users", response_model=list[UserResponse])
def admin_list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    管理员查看所有用户。

    测试要点：
      - admin 角色 → 200
      - 普通用户 → 403
      - 未登录 → 401
    """
    return db.query(User).all()


@router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
def admin_update_role(
    user_id: int,
    data: UserRoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    管理员修改用户角色。

    测试要点：
      - admin 修改用户角色 → 200
      - 普通用户调用 → 403
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.role = data.role
    db.commit()
    db.refresh(user)
    return user
