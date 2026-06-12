"""
3.4 异步数据库操作 — 可运行 Demo

启动方式:
    cd code/阶段3-数据库与ORM/3.4-异步数据库操作
    uvicorn main:app --reload

访问 http://127.0.0.1:8000/docs 交互式测试。

⚠️ 依赖安装:
    pip install aiosqlite sqlalchemy[asyncio] httpx

核心知识点:
  1. 同步 vs 异步：从 create_engine → create_async_engine
  2. 异步 Session: AsyncSession + async_sessionmaker
  3. 异步依赖: async def get_async_db() + async with
  4. 异步 CRUD: 所有数据库操作加 await
  5. 异步端点: async def endpoint(...)
  6. 全链路异步: 从网络请求到数据库查询，无阻塞

curl 测试:
    # 创建用户
    curl -X POST http://127.0.0.1:8000/users/ \
      -H "Content-Type: application/json" \
      -d '{"username":"张三","email":"zhang@example.com","password":"12345678"}'

    curl -X POST http://127.0.0.1:8000/users/ \
      -H "Content-Type: application/json" \
      -d '{"username":"李四","email":"li@example.com","password":"12345678"}'

    # 获取用户列表
    curl http://127.0.0.1:8000/users/

    # 获取单个用户（含文章）
    curl http://127.0.0.1:8000/users/1

    # 创建文章
    curl -X POST http://127.0.0.1:8000/posts/ \
      -H "Content-Type: application/json" \
      -d '{"title":"异步编程笔记","content":"async/await 的原理...","user_id":1}'

    # 获取文章列表（含作者）
    curl http://127.0.0.1:8000/posts/

    # 并发压测（需要先安装 httpx）
    # python benchmark.py
"""

from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import String, Integer, DateTime, ForeignKey, select, func
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, selectinload,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,      # ← sync: create_engine
    AsyncSession,             # ← sync: Session
    async_sessionmaker,       # ← sync: sessionmaker
    AsyncEngine,
)
from pydantic import BaseModel, Field, ConfigDict, EmailStr


# ═══════════════════════════════════════════════════════════
# database_async.py — 异步数据库基础设施
# ═══════════════════════════════════════════════════════════

# 异步 URL：注意 driver 前缀从 "sqlite" 变为 "sqlite+aiosqlite"
DATABASE_URL = "sqlite+aiosqlite:///./blog_async.db"
# 切换 MySQL: DATABASE_URL = "mysql+asyncmy://user:pass@localhost/dbname"

# 异步引擎
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,              # 开发环境打印 SQL
    pool_size=20,           # 异步下连接池可以设大一些
    max_overflow=40,
    pool_pre_ping=True,     # 每次使用前检查连接是否存活
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 异步下建议关闭
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


async def get_async_db():
    """
    异步 FastAPI 依赖——每个请求获取独立的 AsyncSession

    对比同步版本 get_db()：
      - def → async def
      - SessionLocal() → async with AsyncSessionLocal() as session
      - yield db → yield session
    """
    async with AsyncSessionLocal() as session:
        yield session


# ═══════════════════════════════════════════════════════════
# models.py — ORM 模型（异步和同步共用同样的模型定义）
# ═══════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    posts: Mapped[list["Post"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(5000))
    published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    author: Mapped["User"] = relationship(back_populates="posts")


# ═══════════════════════════════════════════════════════════
# schemas.py — Pydantic 模型（同步异步共用，无需改动）
# ═══════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["zhangsan"])
    email: EmailStr = Field(examples=["zhang@example.com"])
    password: str = Field(min_length=6, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    published: bool = False
    user_id: int


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    published: bool
    created_at: datetime
    updated_at: datetime
    user_id: int


class PostWithAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    published: bool
    created_at: datetime
    user_id: int
    author: UserResponse


# ═══════════════════════════════════════════════════════════
# crud_async.py — 异步 CRUD 操作
# ═══════════════════════════════════════════════════════════

async def get_user(db: AsyncSession, user_id: int) -> User | None:
    """异步查用户——注意 await"""
    return await db.get(User, user_id)  # ← session.get() 也要 await


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """异步按邮箱查用户"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """异步分页查用户"""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    )
    return list(result.scalars().all())


async def get_user_with_posts(db: AsyncSession, user_id: int) -> User | None:
    """异步 Eager Loading——用 selectinload 一次性拿用户和文章"""
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.posts))
    )
    return result.scalars().first()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """异步创建用户"""
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password="hashed_" + user_in.password,
    )
    db.add(db_user)
    await db.commit()       # ← commit 必须 await
    await db.refresh(db_user)  # ← refresh 也必须 await
    return db_user


async def get_posts_with_author(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Post]:
    """异步查文章（含作者），用 selectinload 避免 N+1"""
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author))  # ← 异步版用 selectinload 更好
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def create_post(db: AsyncSession, post_in: PostCreate) -> Post:
    """异步创建文章"""
    db_post = Post(**post_in.model_dump())
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return db_post


async def delete_post(db: AsyncSession, post: Post) -> None:
    """异步删除文章"""
    await db.delete(post)
    await db.commit()


# ═══════════════════════════════════════════════════════════
# FastAPI 应用
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="3.4 异步数据库操作 Demo",
    description=(
        "全链路异步：async endpoint → async dependency → async session → async driver"
    ),
    version="1.0.0",
)


@app.on_event("startup")
async def startup():
    """异步启动——异步建表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # ← create_all 是同步的，用 run_sync 包装
    print("✅ 数据库表已就绪（异步引擎）")


# ═══════════════════════════════════════════════
# User 端点（全部 async）
# ═══════════════════════════════════════════════

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["用户管理"])
async def create_user_endpoint(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_async_db),  # ← 注入异步 session
):
    """异步创建用户"""
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    return await create_user(db, user_in)


@app.get("/users/", response_model=list[UserResponse], tags=["用户管理"])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
):
    """异步获取用户列表"""
    return await get_users(db, skip=skip, limit=limit)


@app.get("/users/{user_id}", response_model=UserResponse, tags=["用户管理"])
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """异步获取用户详情（含文章数）"""
    user = await get_user_with_posts(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


# ═══════════════════════════════════════════════
# Post 端点（全部 async）
# ═══════════════════════════════════════════════

@app.post("/posts/", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["文章管理"])
async def create_post_endpoint(
    post_in: PostCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """异步创建文章"""
    user = await get_user(db, post_in.user_id)
    if not user:
        raise HTTPException(status_code=400, detail=f"用户 {post_in.user_id} 不存在")
    return await create_post(db, post_in)


@app.get("/posts/", response_model=list[PostWithAuthor], tags=["文章管理"])
async def read_posts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
):
    """异步获取文章列表（含作者）——一次 SQL 解决 N+1"""
    return await get_posts_with_author(db, skip=skip, limit=limit)


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["文章管理"])
async def delete_post_endpoint(
    post_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """异步删除文章"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    await delete_post(db, post)


# ═══════════════════════════════════════════════
# 对比演示端点
# ═══════════════════════════════════════════════

@app.get("/", tags=["系统"])
async def root():
    return {
        "message": "Async Blog API",
        "docs": "/docs",
        "note": "所有端点都是 async def，全链路异步无阻塞",
        "compare": "回顾 3.2 的 main.py——全部是 def（同步），这里全部是 async def（异步）",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
