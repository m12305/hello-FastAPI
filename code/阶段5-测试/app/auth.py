"""
auth.py — JWT 认证模块（被测试的目标应用）

功能：
  1. 密码哈希 / 验证（bcrypt + passlib）
  2. JWT 令牌生成（python-jose）
  3. JWT 令牌解码与验证
  4. get_current_user 依赖 —— 所有受保护端点的核心依赖
  5. 角色检查依赖 —— RBAC 权限控制

测试时，get_current_user 可以被 dependency_overrides 替换，
无需真实 Token 即可模拟各种用户身份。
"""

import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User


# ═══════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-change-in-production-32chars!!")
ALGORITHM = "HS256"                     # 对称加密算法
ACCESS_TOKEN_EXPIRE_MINUTES = 30        # Token 有效期


# ═══════════════════════════════════════════════════════════
# 密码哈希
# ═══════════════════════════════════════════════════════════

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码 vs 哈希值"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成 bcrypt 密码哈希"""
    return pwd_context.hash(password)


# ═══════════════════════════════════════════════════════════
# JWT 生成
# ═══════════════════════════════════════════════════════════

def create_access_token(data: dict) -> str:
    """
    生成 Access Token

    data 示例: {"sub": "1", "role": "admin"}
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ═══════════════════════════════════════════════════════════
# JWT 验证
# ═══════════════════════════════════════════════════════════

def decode_token(token: str) -> dict:
    """解码并验证 JWT Token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
        )


# ═══════════════════════════════════════════════════════════
# OAuth2 方案（用于 Swagger UI 的 Authorize 按钮）
# ═══════════════════════════════════════════════════════════

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ═══════════════════════════════════════════════════════════
# 核心依赖：get_current_user
# 这是测试中最常被覆盖的依赖！
# ═══════════════════════════════════════════════════════════

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从 JWT Token 中解析当前登录用户。

    检查链条:
      1. Token 是否有效（签名 + 过期）
      2. 用户是否存在
      3. 用户是否被停用（is_active）
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 解码 JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 查用户
    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_exception

    # 停用检查
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被停用",
        )

    return user


# ═══════════════════════════════════════════════════════════
# 角色检查依赖
# ═══════════════════════════════════════════════════════════

class RoleChecker:
    """
    角色检查器 —— 可调用类作为 FastAPI 依赖。

    用法:
        require_admin = RoleChecker(["admin"])

        @app.get("/admin")
        def admin_panel(user=Depends(require_admin)):
            ...
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足！需要 {self.allowed_roles} 角色，当前: {current_user.role}",
            )
        return current_user


# 预定义的检查器 —— 直接用 Depends(require_admin) 等
require_user = RoleChecker(["user", "editor", "admin"])
require_editor = RoleChecker(["editor", "admin"])
require_admin = RoleChecker(["admin"])
