"""
阶段 4：认证与授权 — 综合可运行 Demo

启动方式:
    cd code/阶段4-认证与授权
    pip install sqlalchemy python-jose[cryptography] passlib[bcrypt] python-multipart
    uvicorn main:app --reload

访问 http://127.0.0.1:8000/docs 交互式测试。

项目结构（对照文档 4.2 + 4.3）:
    main.py              ← FastAPI 应用入口 + 全部路由
    database.py           ← 引擎、会话、Base、get_db
    models.py             ← User ORM 模型（含 role + is_active）
    schemas.py            ← Pydantic 模型（请求/响应）
    auth.py               ← JWT 生成/验证、密码哈希、get_current_user
    permissions.py        ← RoleChecker、所有权检查、API Key、多认证

涵盖知识点:
  4.2 JWT 认证:
    - bcrypt 密码哈希
    - JWT Access Token + Refresh Token
    - OAuth2PasswordBearer + OAuth2PasswordRequestForm
    - Token 黑名单（登出）
    - get_current_user 依赖注入
  4.3 权限控制:
    - RBAC 角色模型（user / editor / admin）
    - RoleChecker 工厂类
    - 数据所有权检查（用户只能操作自己的文章）
    - API Key 认证（机器间通信）
    - 多认证方式共存（JWT + API Key）
    - Scope 细粒度权限

curl 测试:
    # ═══ 注册 ═══
    curl -X POST http://127.0.0.1:8000/register \
      -H "Content-Type: application/json" \
      -d '{"username":"admin","email":"admin@example.com","password":"admin123"}'

    curl -X POST http://127.0.0.1:8000/register \
      -H "Content-Type: application/json" \
      -d '{"username":"editor","email":"editor@example.com","password":"editor123"}'

    curl -X POST http://127.0.0.1:8000/register \
      -H "Content-Type: application/json" \
      -d '{"username":"user1","email":"user1@example.com","password":"user1123"}'

    # ═══ 登录（获取 Token）═══
    # 用 Swagger UI 的 /docs 最方便——点右上角 🔓 Authorize 按钮
    # 或者用 curl 表单格式:
    curl -X POST http://127.0.0.1:8000/login \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "grant_type=password&username=admin&password=admin123"

    # 把返回的 access_token 保存为变量
    TOKEN="<access_token>"

    # ═══ 获取当前用户 ═══
    curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/me

    # ═══ 刷新 Token ═══
    curl -X POST http://127.0.0.1:8000/refresh \
      -H "Content-Type: application/json" \
      -d '{"refresh_token":"<refresh_token>"}'

    # ═══ 登出 ═══
    curl -X POST http://127.0.0.1:8000/logout \
      -H "Authorization: Bearer $TOKEN"

    # ═══ 权限控制 ═══
    # 管理员：修改角色
    curl -X PATCH http://127.0.0.1:8000/admin/users/2/role \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"role":"admin"}'

    # 管理员：查看所有用户
    curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/admin/users

    # 普通用户试图访问管理员接口 → 403
    curl -H "Authorization: Bearer $USER_TOKEN" http://127.0.0.1:8000/admin/users

    # ═══ 文章 + 所有权 ═══
    curl -X POST http://127.0.0.1:8000/posts/ \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"title":"我的文章","content":"只有我能修改它"}'

    # ═══ API Key 认证 ═══
    curl -H "X-API-Key: svc-a-abc123def456" http://127.0.0.1:8000/api/external/posts

    # ═══ 混合认证 ═══
    curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/hybrid/whoami
    curl -H "X-API-Key: svc-b-xyz789ghi012" http://127.0.0.1:8000/hybrid/whoami
"""

from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import String, DateTime, ForeignKey, select, func
from sqlalchemy.orm import Session, Mapped, mapped_column, relationship

from database import engine, Base, get_db
from models import User
from schemas import (
    UserCreate, UserResponse, UserRoleUpdate,
    Token, TokenRefresh,
    PostCreate, PostUpdate, PostResponse,
)
from auth import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
    add_to_blacklist,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from permissions import (
    RoleChecker, require_admin, require_editor,
    require_scope, get_api_client, get_current_identity,
)


# ═══════════════════════════════════════════════════════════
# Post 模型（本文件内定义，演示数据所有权）
# ═══════════════════════════════════════════════════════════

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(5000))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author: Mapped["User"] = relationship()


# ═══════════════════════════════════════════════════════════
# FastAPI 应用
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="阶段 4 认证与授权 Demo",
    description=(
        "综合演示 JWT 认证 + RBAC 权限控制 + 数据所有权 + API Key。\n\n"
        "**角色**: user / editor / admin\n"
        "**预置 API Key**: svc-a-abc123def456, svc-b-xyz789ghi012"
    ),
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _seed_data()
    print("✅ 数据库表已就绪，种子数据已填充")


def _seed_data():
    """创建演示用户（如果不存在）"""
    db = SessionLocal()
    try:
        if db.scalar(select(func.count()).select_from(User)):
            return  # 已有数据

        users = [
            User(username="admin", email="admin@example.com",
                 hashed_password=get_password_hash("admin123"), role="admin"),
            User(username="editor", email="editor@example.com",
                 hashed_password=get_password_hash("editor123"), role="editor"),
            User(username="user1", email="user1@example.com",
                 hashed_password=get_password_hash("user1123"), role="user"),
            User(username="user2", email="user2@example.com",
                 hashed_password=get_password_hash("user2123"), role="user"),
        ]
        db.add_all(users)
        db.commit()

        # 给每个用户创建一篇示例文章
        for u in users:
            db.refresh(u)
            db.add(Post(title=f"{u.username}的第一篇文章", content="这是示例内容...", user_id=u.id))
        db.commit()

        print(f"  ✅ 种子数据: {len(users)} 用户 (admin/editor/user1/user2)，密码同用户名+123")
    finally:
        db.close()


from database import SessionLocal  # noqa: E402 (seed 函数用)


# ═══════════════════════════════════════════════════════════
# 1. 注册
# ═══════════════════════════════════════════════════════════

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["🔐 认证"])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册——默认角色为 "user"。

    密码用 bcrypt 哈希后存储，原文不落库。
    """
    # 检查唯一性
    existing = db.scalars(
        select(User).where(
            (User.username == user_in.username) | (User.email == user_in.email)
        )
    ).first()
    if existing:
        field = "用户名" if existing.username == user_in.username else "邮箱"
        raise HTTPException(status_code=400, detail=f"该{field}已被注册")

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ═══════════════════════════════════════════════════════════
# 2. 登录（获取 Token）
# ═══════════════════════════════════════════════════════════

@app.post("/login", response_model=Token, tags=["🔐 认证"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    登录——返回 Access Token + Refresh Token。

    OAuth2PasswordRequestForm 期望表单格式（Swagger UI 自动处理）：
      grant_type=password&username=xxx&password=xxx

    Access Token: 30 分钟有效，每次 API 请求携带
    Refresh Token: 7 天有效，用于获取新 Token
    """
    # 查用户
    user = db.scalars(
        select(User).where(User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用")

    # 生成 Token
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ═══════════════════════════════════════════════════════════
# 3. 刷新 Token
# ═══════════════════════════════════════════════════════════

@app.post("/refresh", response_model=Token, tags=["🔐 认证"])
def refresh_token(token_in: TokenRefresh, db: Session = Depends(get_db)):
    """
    用 Refresh Token 换取新的 Token 对。

    前端流程：
      Access 过期 → 拿 Refresh 调此接口 → 拿到新 Access + Refresh
    """
    try:
        payload = decode_token(token_in.refresh_token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Refresh Token 无效或已过期")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="这不是 Refresh Token")

    user_id = payload.get("sub")
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已停用")

    new_access = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


# ═══════════════════════════════════════════════════════════
# 4. 登出
# ═══════════════════════════════════════════════════════════

@app.post("/logout", tags=["🔐 认证"])
def logout(current_user: User = Depends(get_current_user), token: str = Depends(auth.oauth2_scheme)):
    """登出——将当前 Access Token 加入黑名单"""
    add_to_blacklist(token)
    return {"message": f"用户 {current_user.username} 已登出，Token 已失效"}


# ═══════════════════════════════════════════════════════════
# 5. 获取当前用户（需要登录）
# ═══════════════════════════════════════════════════════════

@app.get("/me", response_model=UserResponse, tags=["👤 用户"])
def read_current_user(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息——任何登录用户均可访问"""
    return current_user


# ═══════════════════════════════════════════════════════════
# 6. 管理员端点
# ═══════════════════════════════════════════════════════════

@app.get("/admin/users", response_model=list[UserResponse], tags=["🔧 管理员"])
def admin_list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员查看所有用户列表——仅 admin 可访问"""
    return list(db.scalars(select(User)).all())


@app.patch("/admin/users/{user_id}/role", response_model=UserResponse, tags=["🔧 管理员"])
def admin_update_role(
    user_id: int,
    role_in: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员修改用户角色——仅 admin 可访问"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    user.role = role_in.role
    db.commit()
    db.refresh(user)
    return user


@app.patch("/admin/users/{user_id}/toggle-active", tags=["🔧 管理员"])
def admin_toggle_active(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员停用/启用用户——仅 admin 可访问"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能停用自己的账号")

    user.is_active = not user.is_active
    db.commit()
    return {"message": f"用户 {user.username} 已{'启用' if user.is_active else '停用'}"}


# ═══════════════════════════════════════════════════════════
# 7. 文章 CRUD（演示数据所有权 + 角色控制）
# ═══════════════════════════════════════════════════════════

@app.post("/posts/", response_model=PostResponse, status_code=201, tags=["📝 文章"])
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),  # ← 只有 editor/admin 能发文
):
    """创建文章——需要 editor 及以上角色"""
    post = Post(**post_in.model_dump(), user_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/posts/", response_model=list[PostResponse], tags=["📝 文章"])
def list_posts(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ← 任何登录用户都能看
):
    """查看文章列表——任何登录用户均可"""
    return list(db.scalars(
        select(Post).offset(skip).limit(limit).order_by(Post.created_at.desc())
    ).all())


@app.get("/posts/{post_id}", response_model=PostResponse, tags=["📝 文章"])
def get_post(post_id: int, db: Session = Depends(get_db)):
    """查看文章详情——无需登录"""
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return post


@app.patch("/posts/{post_id}", response_model=PostResponse, tags=["📝 文章"])
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新文章——仅文章作者或管理员可操作。

    演示数据所有权检查：用户只能改自己的文章。
    """
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    # ── 所有权检查 ──
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你只能修改自己的文章",
        )

    update_data = post_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["📝 文章"])
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除文章——仅文章作者或管理员可操作。

    使用 require_scope 做更细粒度的演示（等价于所有权检查）。
    """
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="你只能删除自己的文章")

    db.delete(post)
    db.commit()


# ═══════════════════════════════════════════════════════════
# 8. API Key 认证端点
# ═══════════════════════════════════════════════════════════

@app.get("/api/external/posts", tags=["🤖 外部 API"])
def external_list_posts(
    db: Session = Depends(get_db),
    client: dict = Depends(get_api_client),
):
    """
    外部服务接口——使用 X-API-Key 认证（不需要 JWT）。

    预置 Key:
      svc-a-abc123def456 → 可读 users + posts
      svc-b-xyz789ghi012 → 可读 users + posts + 写 posts
    """
    posts = list(db.scalars(
        select(Post).limit(50).order_by(Post.created_at.desc())
    ).all())

    return {
        "source": client["name"],
        "auth_method": "API Key",
        "count": len(posts),
        "posts": [{"id": p.id, "title": p.title, "user_id": p.user_id} for p in posts],
    }


# ═══════════════════════════════════════════════════════════
# 9. 混合认证端点（JWT 或 API Key 任意一种即可）
# ═══════════════════════════════════════════════════════════

@app.get("/hybrid/whoami", tags=["🔄 混合认证"])
def hybrid_whoami(identity: dict = Depends(get_current_identity)):
    """
    混合认证端点——支持 Bearer Token 或 X-API-Key。

    返回当前请求的身份信息。
    """
    if identity["type"] == "user":
        user = identity["user"]
        return {
            "auth_type": "JWT (用户)",
            "username": user.username,
            "role": user.role,
            "email": user.email,
        }
    else:
        return {
            "auth_type": "API Key (服务)",
            "service_name": identity["name"],
            "permissions": identity.get("permissions", []),
        }


# ═══════════════════════════════════════════════════════════
# 根路由
# ═══════════════════════════════════════════════════════════

@app.get("/", tags=["系统"])
def root():
    return {
        "message": "阶段 4 认证与授权 Demo",
        "docs": "/docs",
        "seeds": {
            "admin": "admin123",
            "editor": "editor123",
            "user1": "user1123",
            "user2": "user2123",
        },
        "api_keys": {
            "svc-a-abc123def456": "read users + posts",
            "svc-b-xyz789ghi012": "read users + posts + write posts",
        },
        "flow": "注册 → 登录(拿 Token) → /me(验证) → /admin/*(权限) → /logout(登出)",
    }


# ═══════════════════════════════════════════════════════════
# 需要把 auth 的 oauth2_scheme 也暴露给 logout 端点
# ═══════════════════════════════════════════════════════════
import auth  # noqa: E402


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
