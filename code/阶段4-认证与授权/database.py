"""
database.py — 数据库基础设施

引擎、会话工厂、Base 基类、get_db 依赖。
和阶段 3 相同的基础设施，直接复用。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

DATABASE_URL = "sqlite:///./auth_demo.db"
# DATABASE_URL = "mysql+pymysql://user:pass@localhost/dbname"

engine = create_engine(
    DATABASE_URL,
    echo=True,          # 开发环境打印 SQL——观察认证流程中的数据库查询
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖——每个请求独立 Session，响应后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
