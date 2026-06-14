"""
models.py — ORM 数据模型（被测试的目标应用）

定义两个模型：
  - User：用户（有角色字段，用于权限测试）
  - Post：文章（有 user_id 外键，用于所有权测试）
"""

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class User(Base):
    """
    用户模型

    字段说明：
      - id: 主键
      - username: 用户名（唯一，3-50 字符）
      - email: 邮箱
      - hashed_password: bcrypt 密码哈希（绝不能返回给前端）
      - role: 角色（user / editor / admin）
      - is_active: 是否启用（停用后不能登录）
      - created_at: 注册时间
      - posts: 关联的文章（一对多）
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联：一个用户有多篇文章
    posts: Mapped[list["Post"]] = relationship(
        "Post", back_populates="author", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Post(Base):
    """
    文章模型

    字段说明：
      - user_id: 外键 → users.id（文章属于谁）
      - title: 标题
      - content: 正文
      - created_at: 创建时间
      - author: 关联的用户（多对一）
    """
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联：文章属于一个用户
    author: Mapped["User"] = relationship("User", back_populates="posts")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"
