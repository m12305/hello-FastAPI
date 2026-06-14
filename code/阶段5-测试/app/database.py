"""
database.py — 数据库配置（被测试的目标应用）

本文件是"被测试系统"的数据库层。
测试时通过 dependency_overrides 替换为 SQLite :memory:，
无需修改本文件即可实现测试隔离。

架构:
  app.dependency_overrides[get_db] = override_test_db  ← 在 conftest.py 中完成
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── 数据库 URL：默认 SQLite 文件库，测试时通过环境变量切换到内存库 ──
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"  # 默认：项目根目录的 SQLite 文件
)

# ── 引擎配置 ──
# SQLite 需要 check_same_thread=False 才能在 FastAPI 中使用
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # 设为 True 可查看 SQL 日志（调试用）
)

# ── 会话工厂 ──
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── 基类（所有 ORM 模型继承自此）──
class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类"""
    pass


# ═══════════════════════════════════════════════════════════
# 核心依赖：get_db（FastAPI 依赖注入用）
# ═══════════════════════════════════════════════════════════

def get_db():
    """
    获取数据库会话（yield 模式）。

    使用 Depends(get_db) 注入到端点函数中，
    请求结束时自动关闭会话，防止连接泄漏。

    测试时，这个函数会被 conftest.py 中的 override_test_db 替换。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
