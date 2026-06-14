"""
app/main.py — FastAPI 应用入口（被测试的目标应用）

这是阶段 5 测试 Demo 的"被测系统"，提供完整的用户+文章 API。

端点分组：
  1. 认证：POST /register, POST /login                → routers/users.py
  2. 用户：GET /users, PATCH /users/{id}, DELETE ...  → routers/users.py
  3. 管理员：GET /admin/users, PATCH /admin/users/...  → routers/users.py
  4. 文章：POST /posts, GET /posts, PATCH /posts ...   → routers/posts.py
  5. Mock演示：GET /weather                            → routers/posts.py

启动方式：
  cd code/阶段5-测试
  pip install fastapi uvicorn sqlalchemy python-jose[cryptography] passlib[bcrypt]
  uvicorn app.main:app --reload

运行测试：
  pip install httpx pytest pytest-cov
  pytest tests/ -v
"""

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app.models import User, Post
from app.auth import get_password_hash
from app.routers import users, posts

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="阶段5-测试 Demo",
    description="FastAPI 测试教学项目 —— 被测试的目标应用",
    version="1.0.0",
)

# ── 注册路由 ──
app.include_router(users.router)
app.include_router(posts.router)


# ═══════════════════════════════════════════════════════════
# 启动事件：建表 + 种子数据
# ═══════════════════════════════════════════════════════════

@app.on_event("startup")
def on_startup():
    """启动时自动建表 + 填充种子数据"""
    Base.metadata.create_all(bind=engine)
    _seed_data()


def _seed_data():
    """
    插入测试用的种子数据（只在表为空时执行）。

    预置账号：
      admin  / admin123  (admin)
      editor / editor123 (editor)
      user1  / user1123  (user)
      user2  / user2123  (user)
    """
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return  # 已有数据，跳过

        # 创建测试用户
        admin = User(
            username="admin", email="admin@test.com",
            hashed_password=get_password_hash("admin123"),
            role="admin", is_active=True,
        )
        editor = User(
            username="editor", email="editor@test.com",
            hashed_password=get_password_hash("editor123"),
            role="editor", is_active=True,
        )
        user1 = User(
            username="user1", email="user1@test.com",
            hashed_password=get_password_hash("user1123"),
            role="user", is_active=True,
        )
        user2 = User(
            username="user2", email="user2@test.com",
            hashed_password=get_password_hash("user2123"),
            role="user", is_active=True,
        )
        db.add_all([admin, editor, user1, user2])
        db.commit()

        # 为 user1 创建一篇示例文章
        post = Post(
            title="第一篇文章",
            content="这是 user1 的第一篇文章，用于测试所有权。",
            user_id=user1.id,
        )
        db.add(post)
        db.commit()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
