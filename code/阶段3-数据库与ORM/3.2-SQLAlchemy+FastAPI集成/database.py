"""
database.py — 引擎、会话工厂、Base、get_db 依赖

FastAPI 集成最关键的基础设施层。
整个应用只创建一个引擎实例，每个请求获取独立的 Session。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# 数据库 URL（生产环境从环境变量读取）
DATABASE_URL = "sqlite:///./blog.db"
# DATABASE_URL = "mysql+pymysql://user:pass@localhost/dbname"

# 引擎（整个应用只创建一次）
engine = create_engine(
    DATABASE_URL,
    echo=True,              # 开发环境打印 SQL
    pool_size=5,            # 连接池大小
    max_overflow=10,        # 最大溢出连接数
)

# Session 工厂
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,        # 手动 flush
    autocommit=False,       # 手动 commit
)


# 所有 ORM 模型的基类
class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════
# FastAPI 依赖——每个请求获取独立的 Session
# ═══════════════════════════════════════════
def get_db():
    """FastAPI 依赖：请求到达时创建 session，响应返回后自动关闭"""
    db = SessionLocal()
    try:
        yield db              # ← 端点使用这个 db
    finally:
        db.close()            # ← 无论成功与否，都关闭连接
