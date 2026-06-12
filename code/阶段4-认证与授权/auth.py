"""
auth.py — JWT 认证核心模块

负责：
  1. 密码哈希与验证（bcrypt via passlib）
  2. JWT 令牌的生成（access + refresh）
  3. JWT 令牌的验证与解码
  4. get_current_user 依赖（所有受保护端点共用）
  5. Token 黑名单（登出机制）
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
# 配置（生产环境从环境变量读取）
# ═══════════════════════════════════════════════════════════

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production-min-32-chars!!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30    # Access Token: 30 分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7       # Refresh Token: 7 天


# ═══════════════════════════════════════════════════════════
# 密码哈希
# ═══════════════════════════════════════════════════════════

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成 bcrypt 密码哈希"""
    return pwd_context.hash(password)


# ═══════════════════════════════════════════════════════════
# JWT 生成
# ═══════════════════════════════════════════════════════════

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    生成 Access Token

    data 示例: {"sub": "1", "role": "admin"}
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    生成 Refresh Token（有效期更长，只用于换取新 Token）
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ═══════════════════════════════════════════════════════════
# JWT 验证
# ═══════════════════════════════════════════════════════════

def decode_token(token: str) -> dict:
    """解码并验证 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 无效或已过期: {e}",
        )


# ═══════════════════════════════════════════════════════════
# Token 黑名单（内存版，生产环境用 Redis）
# ═══════════════════════════════════════════════════════════

TOKEN_BLACKLIST: set[str] = set()


def add_to_blacklist(token: str) -> None:
    """将 Token 加入黑名单（登出时调用）"""
    TOKEN_BLACKLIST.add(token)


def is_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单中"""
    return token in TOKEN_BLACKLIST


# ═══════════════════════════════════════════════════════════
# OAuth2 方案
# ═══════════════════════════════════════════════════════════

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login",   # ← Swagger UI 会自动跳转到此端点获取 Token
)


# ═══════════════════════════════════════════════════════════
# 核心依赖：获取当前用户
# ═══════════════════════════════════════════════════════════

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从 JWT Token 中解析当前登录用户。

    这是整个认证系统的核心依赖——所有需要登录的端点都用它。
    检查链条:
      1. Token 是否在黑名单中（已登出）
      2. Token 是否有效（签名 + 过期）
      3. 用户是否存在
      4. 用户是否被停用（is_active）
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 黑名单检查
    if is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效（已登出）",
        )

    # JWT 解码
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
            detail="账号已被停用，请联系管理员",
        )

    return user
