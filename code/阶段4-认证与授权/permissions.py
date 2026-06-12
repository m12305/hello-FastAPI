"""
permissions.py — 权限控制模块

实现三层权限体系：
  1. 角色检查（RBAC）：RoleChecker 工厂类
  2. 数据所有权：用户只能操作自己的资源
  3. API Key 认证：机器间通信
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from auth import get_current_user, decode_token
from database import get_db
from models import User


# ═══════════════════════════════════════════════════════════
# 1. 角色检查（RBAC）—— RoleChecker 工厂类
# ═══════════════════════════════════════════════════════════

class RoleChecker:
    """
    角色检查器工厂类。

    用法:
        require_admin = RoleChecker(["admin"])
        require_editor = RoleChecker(["editor", "admin"])

        @app.get("/admin")
        def admin_panel(user = Depends(require_admin)):
            ...
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            allowed_str = " / ".join(self.allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足！需要 {allowed_str} 角色，当前角色: {current_user.role}",
            )
        return current_user


# 预定义的角色检查依赖——直接在各端点使用
require_user = RoleChecker(["user", "editor", "admin"])       # 所有登录用户
require_editor = RoleChecker(["editor", "admin"])              # 编辑者及以上
require_admin = RoleChecker(["admin"])                          # 仅管理员


# ═══════════════════════════════════════════════════════════
# 2. Scope 权限检查（比角色更细粒度）
# ═══════════════════════════════════════════════════════════

# 权限定义
SCOPES = {
    "users:read": "查看用户信息",
    "users:write": "创建/修改用户",
    "users:delete": "删除用户",
    "posts:read": "查看文章",
    "posts:write": "创建/修改文章",
}

# 角色 → Scope 映射
ROLE_SCOPES = {
    "user": ["users:read", "posts:read"],
    "editor": ["users:read", "posts:read", "posts:write"],
    "admin": list(SCOPES.keys()),  # admin 拥有所有权限
}


def require_scope(required_scope: str):
    """
    Scope 权限检查——比角色更细粒度。

    用法:
        @app.delete("/users/{user_id}")
        def delete_user(user = Depends(require_scope("users:delete"))):
            ...
    """
    def scope_checker(current_user: User = Depends(get_current_user)):
        user_scopes = ROLE_SCOPES.get(current_user.role, [])
        if required_scope not in user_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限: {required_scope} ({SCOPES.get(required_scope, '')})，当前角色: {current_user.role}",
            )
        return current_user
    return scope_checker


# ═══════════════════════════════════════════════════════════
# 3. 数据所有权检查
# ═══════════════════════════════════════════════════════════

def require_owner_or_admin(resource_owner_id: int):
    """
    检查当前用户是资源的所有者 或 管理员。

    用法:
        # 在端点内调用
        require_owner_or_admin(post.user_id)(current_user)

    也可以直接包装成依赖：
        post = get_post(...)
        if post.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(403, "只能操作自己的资源")
    """
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role == "admin":
            return current_user  # 管理员通行
        if current_user.id != resource_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="你只能操作自己的资源",
            )
        return current_user
    return checker


# ═══════════════════════════════════════════════════════════
# 4. API Key 认证（机器间通信）
# ═══════════════════════════════════════════════════════════

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# 模拟 API Key 存储（实际项目存数据库）
VALID_API_KEYS = {
    "svc-a-abc123def456": {
        "name": "Service A",
        "permissions": ["users:read", "posts:read"],
    },
    "svc-b-xyz789ghi012": {
        "name": "Service B",
        "permissions": ["users:read", "posts:read", "posts:write"],
    },
}


def get_api_client(
    api_key: str | None = Security(api_key_header),
) -> dict:
    """验证 API Key——用于服务间调用，不需要 JWT"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 X-API-Key 请求头",
        )
    client = VALID_API_KEYS.get(api_key)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key",
        )
    return client


# ═══════════════════════════════════════════════════════════
# 5. 多认证方式共存
# ═══════════════════════════════════════════════════════════

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/login",
    auto_error=False,  # ← 关键：不强制要求
)


def get_current_identity(
    token: str | None = Security(oauth2_scheme_optional),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> dict:
    """
    统一认证入口——支持 JWT（用户）或 API Key（服务）。

    返回统一格式:
      {"type": "user", "user": User(...)}
      {"type": "service", "name": "Service A", "permissions": [...]}
    """
    # 优先检查 JWT
    if token:
        try:
            payload = decode_token(token)
            user = db.get(User, int(payload["sub"]))
            if user and user.is_active:
                return {"type": "user", "user": user}
        except Exception:
            pass  # JWT 失败，再试 API Key

    # 再检查 API Key
    if api_key:
        client = VALID_API_KEYS.get(api_key)
        if client:
            return {"type": "service", **client}

    # 都失败
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="请提供有效的 Bearer Token 或 X-API-Key",
        headers={"WWW-Authenticate": "Bearer"},
    )
