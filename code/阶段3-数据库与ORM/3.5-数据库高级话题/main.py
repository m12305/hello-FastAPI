"""
3.5 数据库高级话题 — 可运行 Demo

启动方式:
    cd code/阶段3-数据库与ORM/3.5-数据库高级话题
    uvicorn main:app --reload

访问 http://127.0.0.1:8000/docs 交互式测试。

本 Demo 涵盖生产级数据库开发的全部核心技巧:
  1. 索引设计 — 单列索引、复合索引、用 EXPLAIN 分析查询
  2. 事务管理 — commit/rollback、savepoint 嵌套事务
  3. N+1 问题 — joinedload vs selectinload 决策树
  4. 分页 — offset 分页（通用）+ cursor 分页（大数据量）
  5. 软删除 — SoftDeleteMixin + 恢复/回收站
  6. Repository 模式 — 通用 BaseRepository + 专用 UserRepository

curl 测试:
    # ─── 索引 ───
    curl http://127.0.0.1:8000/index-demo/users-by-email?email=alice@example.com
    curl http://127.0.0.1:8000/index-demo/explain?email=alice@example.com

    # ─── 事务 ───
    curl -X POST http://127.0.0.1:8000/transaction-demo/transfer \
      -H "Content-Type: application/json" \
      -d '{"from_user_id":1,"to_user_id":2,"amount":500}'

    curl -X POST http://127.0.0.1:8000/transaction-demo/transfer \
      -H "Content-Type: application/json" \
      -d '{"from_user_id":1,"to_user_id":2,"amount":50000}'  # 余额不足

    # ─── N+1 对比 ───
    curl "http://127.0.0.1:8000/n1-demo/posts-lazy"       # N+1（观察控制台 SQL）
    curl "http://127.0.0.1:8000/n1-demo/posts-eager"      # 1 次 JOIN（观察控制台 SQL）

    # ─── 分页 ───
    curl "http://127.0.0.1:8000/products/?page=1&page_size=5"
    curl "http://127.0.0.1:8000/products/?page=2&page_size=5"
    curl "http://127.0.0.1:8000/products/cursor?cursor=&page_size=5"

    # ─── 软删除 ───
    curl -X DELETE http://127.0.0.1:8000/products/3
    curl -X POST http://127.0.0.1:8000/products/3/restore

    # ─── Repository 模式 ───
    curl -X POST http://127.0.0.1:8000/repo-demo/users/ \
      -H "Content-Type: application/json" \
      -d '{"username":"新用户","email":"new@example.com","password":"12345678"}'
    curl http://127.0.0.1:8000/repo-demo/users/
"""

from typing import TypeVar, Generic
from datetime import datetime
from contextlib import contextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy import (
    create_engine, String, Integer, Float, Boolean, DateTime, ForeignKey,
    select, func, update, delete, Index, text,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, Session, sessionmaker,
    relationship, joinedload, selectinload,
)
from pydantic import BaseModel, Field, ConfigDict


# ═══════════════════════════════════════════════════════════
# database.py
# ═══════════════════════════════════════════════════════════

DATABASE_URL = "sqlite:///./advanced.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 1. 索引设计演示
# ═══════════════════════════════════════════════════════════

class User(Base):
    """
    用户模型 — 演示索引设计策略

    索引策略:
      - username, email: 单列索引（用于精确查找和唯一约束）
      - (email, is_active): 复合索引（用于"查活跃用户"这类组合查询）
      - created_at: 单列索引（用于时间排序）
    """
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),  # 复合索引
        Index("ix_users_created", "created_at"),               # 时间索引
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    balance: Mapped[float] = mapped_column(Float, default=1000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(Base):
    """文章模型 — 外键列加索引"""
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(5000))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True  # ← 外键列必须加索引
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author: Mapped["User"] = relationship(back_populates="posts")


# ═══════════════════════════════════════════════════════════
# 5. 软删除 — Mixin 模式
# ═══════════════════════════════════════════════════════════

class SoftDeleteMixin:
    """
    软删除 Mixin——嵌入任何模型即可获得软删除能力

    核心理念：
      硬删除 (DELETE)     → 数据永久消失，无法恢复
      软删除 (标记删除)   → 数据仍在，标记 is_deleted=True
         ✅ 可恢复（回收站）
         ✅ 保留审计记录
         ⚠️ 所有查询记得加 WHERE is_deleted = False
    """
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    def soft_delete(self):
        """标记为已删除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """恢复已删除的记录"""
        self.is_deleted = False
        self.deleted_at = None


class Product(Base, SoftDeleteMixin):
    """商品模型 — 演示软删除 + Repository"""
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_name", "name"),              # 商品名搜索
        Index("ix_products_category_price", "category", "price"),  # 分类+价格筛选
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ═══════════════════════════════════════════════════════════
# 6. Repository 模式
# ═══════════════════════════════════════════════════════════

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    通用 Repository 基类——把重复的 CRUD 代码抽象到这里

    对比传统的 crud.py：
      get_user(db, id)     → repo.get(id)
      get_product(db, id)  → repo.get(id)   ← 同一个方法！
    """

    def __init__(self, model: type[T], db: Session):
        self.model = model
        self.db = db

    # ── Read ──

    def get(self, id: int) -> T | None:
        return self.db.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def find_by(self, **kwargs) -> list[T]:
        stmt = select(self.model).filter_by(**kwargs)
        return list(self.db.scalars(stmt).all())

    def find_one_by(self, **kwargs) -> T | None:
        stmt = select(self.model).filter_by(**kwargs)
        return self.db.scalars(stmt).first()

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(self.model))

    # ── Create ──

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    # ── Update ──

    def update(self, instance: T, **kwargs) -> T:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    # ── Delete ──

    def delete(self, instance: T) -> None:
        self.db.delete(instance)
        self.db.commit()

    def delete_by_id(self, id: int) -> bool:
        instance = self.get(id)
        if instance:
            self.delete(instance)
            return True
        return False


class UserRepository(BaseRepository[User]):
    """User 专用 Repository——继承基类，添加 User 特有方法"""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        return self.find_one_by(email=email)

    def get_active_users(self) -> list[User]:
        return self.find_by(is_active=True)

    def get_with_posts(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.posts))
        )
        return self.db.scalars(stmt).first()

    def deactivate(self, user_id: int) -> User | None:
        user = self.get(user_id)
        if user:
            return self.update(user, is_active=False)
        return None


# ═══════════════════════════════════════════════════════════
# Pydantic Schemas
# ═══════════════════════════════════════════════════════════

class TransferRequest(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: float = Field(gt=0, description="转账金额，必须大于 0")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    password: str = Field(min_length=6)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    is_active: bool
    balance: float
    created_at: datetime


class PostWithAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    created_at: datetime
    user_id: int
    author: UserResponse


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    price: float
    stock: int
    category: str
    is_deleted: bool
    created_at: datetime


class Page(BaseModel, Generic[T]):
    """通用分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class CursorPage(BaseModel, Generic[T]):
    """Cursor 分页响应"""
    items: list[T]
    has_next: bool
    next_cursor: str | None


# ═══════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="3.5 数据库高级话题 Demo",
    description="索引 · 事务 · N+1 · 分页 · 软删除 · Repository 模式",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _seed_data()
    print("✅ 数据库表已就绪，种子数据已填充")


def _seed_data():
    """填充演示数据"""
    db = SessionLocal()
    try:
        if db.scalar(select(func.count()).select_from(User)):
            return  # 已有数据，跳过

        # 用户
        users = [
            User(username="Alice", email="alice@example.com", hashed_password="hp1", balance=5000),
            User(username="Bob", email="bob@example.com", hashed_password="hp2", balance=3000),
            User(username="Charlie", email="charlie@example.com", hashed_password="hp3", balance=1000),
            User(username="Diana", email="diana@example.com", hashed_password="hp4", balance=8000),
            User(username="Eve", email="eve@example.com", hashed_password="hp5", balance=2000),
            User(username="Frank", email="frank@example.com", hashed_password="hp6", balance=500, is_active=False),
            User(username="Grace", email="grace@example.com", hashed_password="hp7", balance=10000),
            User(username="Henry", email="henry@example.com", hashed_password="hp8", balance=1500),
        ]
        db.add_all(users)
        db.commit()
        for u in users:
            db.refresh(u)

        # 文章
        posts = []
        for i, u in enumerate(users[:5]):
            for j in range(3):
                posts.append(Post(
                    title=f"{u.username}的文章-{j+1}",
                    content=f"这是 {u.username} 的第 {j+1} 篇文章。这里有很多内容...",
                    user_id=u.id,
                ))
        db.add_all(posts)

        # 商品
        categories = ["电子产品", "图书", "服装", "食品", "家居"]
        products = []
        for i in range(30):
            cat = categories[i % len(categories)]
            products.append(Product(
                name=f"{cat}商品-{i+1:02d}",
                description=f"这是 {cat} 分类下的第 {i+1} 个商品",
                price=round(10 + (i * 37.5) % 500, 2),
                stock=10 + i * 3,
                category=cat,
            ))
        # 给第 3 个商品做软删除
        products[2].is_deleted = True
        products[2].deleted_at = datetime.utcnow()

        db.add_all(products)
        db.commit()
        print(f"  ✅ 种子数据: {len(users)} 用户, {len(posts)} 文章, {len(products)} 商品")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 路由 1: 索引演示
# ═══════════════════════════════════════════════════════════

@app.get("/index-demo/users-by-email", tags=["1. 索引演示"])
def find_user_by_email(email: str, db: Session = Depends(get_db)):
    """
    按邮箱查找用户——观察控制台 SQL 输出。

    如果输出包含 USING INDEX，说明索引生效。
    把 echo=False 改成 echo=True 可以看到实际 SQL。
    """
    user = db.scalars(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return UserResponse.model_validate(user)


@app.get("/index-demo/explain", tags=["1. 索引演示"])
def explain_query(email: str, db: Session = Depends(get_db)):
    """
    用 EXPLAIN QUERY PLAN 分析查询是否走索引。

    返回结果中:
      USING INDEX → ✅ 索引生效
      SCAN → ❌ 全表扫描
    """
    result = db.execute(
        text("EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = :email"),
        {"email": email},
    )
    plan_lines = [row[0] for row in result]

    # 获取表上的索引信息
    indexes = []
    for table_name in ["users", "products"]:
        idx_result = db.execute(text(f"PRAGMA index_list({table_name})"))
        indexes.extend([
            {"table": table_name, "name": row[1], "unique": bool(row[2])}
            for row in idx_result
        ])

    return {
        "query": f"SELECT * FROM users WHERE email = '{email}'",
        "query_plan": plan_lines,
        "uses_index": any("USING INDEX" in line for line in plan_lines),
        "all_indexes": indexes,
    }


# ═══════════════════════════════════════════════════════════
# 路由 2: 事务管理演示
# ═══════════════════════════════════════════════════════════

@app.post("/transaction-demo/transfer", tags=["2. 事务演示"])
def transfer_money(req: TransferRequest, db: Session = Depends(get_db)):
    """
    转账——演示事务的原子性。

    扣钱 + 加钱 + 写日志三个操作在一个事务中，
    任何一个失败都全部回滚。
    """
    from_user = db.get(User, req.from_user_id)
    to_user = db.get(User, req.to_user_id)

    if not from_user:
        raise HTTPException(404, f"转出用户 {req.from_user_id} 不存在")
    if not to_user:
        raise HTTPException(404, f"转入用户 {req.to_user_id} 不存在")
    if from_user.id == to_user.id:
        raise HTTPException(400, "不能给自己转账")
    if from_user.balance < req.amount:
        raise HTTPException(
            400,
            f"余额不足: {from_user.username} 只有 {from_user.balance}，需要 {req.amount}"
        )

    # 使用 savepoint 做嵌套事务
    savepoint = db.begin_nested()  # ← 保存点
    try:
        # 操作 1: 扣钱
        from_user.balance -= req.amount

        # 操作 2: 加钱
        to_user.balance += req.amount

        # 操作 3: 记日志（模拟）
        # 如果金额 > 10000，触发"风控"回滚
        if req.amount > 10000:
            raise ValueError("单笔转账超过风控限额")

        db.commit()  # ← 三个操作一起提交
        db.refresh(from_user)
        db.refresh(to_user)

        return {
            "status": "success",
            "from": {"id": from_user.id, "name": from_user.username, "balance": from_user.balance},
            "to": {"id": to_user.id, "name": to_user.username, "balance": to_user.balance},
            "amount": req.amount,
        }

    except Exception as e:
        db.rollback()  # ← 全部回滚（包括 savepoint）
        raise HTTPException(500, f"转账失败，已回滚: {e}")


@app.get("/transaction-demo/users", response_model=list[UserResponse], tags=["2. 事务演示"])
def get_all_users(db: Session = Depends(get_db)):
    """查看所有用户的余额"""
    return list(db.scalars(select(User).order_by(User.id)).all())


# ═══════════════════════════════════════════════════════════
# 路由 3: N+1 问题演示
# ═══════════════════════════════════════════════════════════

@app.get("/n1-demo/posts-lazy", response_model=list[PostWithAuthor], tags=["3. N+1 演示"])
def posts_lazy(db: Session = Depends(get_db)):
    """
    ❌ Lazy Loading —— N+1 查询问题

    把 echo=True 后观察控制台:
      1 次 SELECT posts
      N 次 SELECT users（每个 post 查一次 author）
    """
    posts = db.scalars(select(Post).limit(10)).all()
    # 下面这行看似无害，实际触发了 N 次数据库查询
    result = [
        PostWithAuthor.model_validate(p) for p in posts
    ]
    return result


@app.get("/n1-demo/posts-eager", response_model=list[PostWithAuthor], tags=["3. N+1 演示"])
def posts_eager(db: Session = Depends(get_db)):
    """
    ✅ Eager Loading —— 一次 SQL 解决

    使用 joinedload(Post.author) 做 LEFT JOIN，
    一次 SQL 拿回所有文章 + 对应的作者数据。
    """
    stmt = (
        select(Post)
        .options(joinedload(Post.author))  # ← 关键：LEFT JOIN users
        .order_by(Post.created_at.desc())
        .limit(10)
    )
    posts = list(db.scalars(stmt).unique().all())
    result = [
        PostWithAuthor.model_validate(p) for p in posts
    ]
    return result


# ═══════════════════════════════════════════════════════════
# 路由 4: 分页演示
# ═══════════════════════════════════════════════════════════

@app.get("/products/", response_model=Page[ProductResponse], tags=["4. 分页演示"])
def list_products_offset(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    category: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Offset 分页（最常见）

    用法：?page=1&page_size=10&category=电子产品
    """
    stmt = select(Product).where(
        Product.is_deleted == False,  # ← 软删除过滤
    )

    if category:
        stmt = stmt.where(Product.category == category)

    # 查总数
    count_stmt = stmt.with_only_columns(func.count()).order_by(None)
    total = db.scalar(count_stmt)

    # 分页
    offset = (page - 1) * page_size
    items = db.scalars(
        stmt.order_by(Product.created_at.desc()).offset(offset).limit(page_size)
    ).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@app.get("/products/cursor", response_model=CursorPage[ProductResponse], tags=["4. 分页演示"])
def list_products_cursor(
    cursor: str = Query(default="", description="上一页最后一项的 id"),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Cursor 分页（大数据量专用）

    用 WHERE id > cursor 代替 OFFSET，性能不受页码增长影响。

    用法：
      第一页: /products/cursor?cursor=&page_size=10
      下一页: /products/cursor?cursor=<next_cursor>&page_size=10
    """
    stmt = select(Product).where(Product.is_deleted == False)

    # cursor 分页：WHERE id > cursor
    if cursor:
        try:
            cursor_id = int(cursor)
            stmt = stmt.where(Product.id > cursor_id)
        except ValueError:
            raise HTTPException(400, "无效的 cursor 值")

    # 多查一条判断是否有下一页
    items = db.scalars(
        stmt.order_by(Product.id.asc()).limit(page_size + 1)
    ).all()

    has_next = len(items) > page_size
    if has_next:
        items = items[:page_size]

    next_cursor = str(items[-1].id) if items else None

    return {
        "items": items,
        "has_next": has_next,
        "next_cursor": next_cursor if has_next else None,
    }


# ═══════════════════════════════════════════════════════════
# 路由 5: 软删除演示
# ═══════════════════════════════════════════════════════════

@app.delete("/products/{product_id}", status_code=status.HTTP_200_OK, tags=["5. 软删除演示"])
def soft_delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    软删除商品——数据仍在数据库中，仅标记 is_deleted=True

    对比硬删除: DELETE FROM products WHERE id=?
    软删除:    UPDATE products SET is_deleted=1, deleted_at=NOW()
    """
    product = db.get(Product, product_id)
    if not product or product.is_deleted:
        raise HTTPException(404, "商品不存在或已被删除")

    product.soft_delete()
    db.commit()

    return {
        "message": f"商品 '{product.name}' 已软删除",
        "can_restore": True,
    }


@app.post("/products/{product_id}/restore", tags=["5. 软删除演示"])
def restore_product(product_id: int, db: Session = Depends(get_db)):
    """恢复已软删除的商品（从回收站还原）"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "商品不存在")
    if not product.is_deleted:
        raise HTTPException(400, "该商品未被删除，无需恢复")

    product.restore()
    db.commit()

    return {
        "message": f"商品 '{product.name}' 已恢复",
        "product": ProductResponse.model_validate(product),
    }


@app.get("/products/deleted", response_model=list[ProductResponse], tags=["5. 软删除演示"])
def list_deleted_products(db: Session = Depends(get_db)):
    """查看已软删除的商品（回收站）"""
    return list(db.scalars(
        select(Product).where(Product.is_deleted == True)
    ).all())


# ═══════════════════════════════════════════════════════════
# 路由 6: Repository 模式演示
# ═══════════════════════════════════════════════════════════

def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    """依赖注入：获取 UserRepository 实例"""
    return UserRepository(db)


@app.post("/repo-demo/users/", response_model=UserResponse, status_code=201, tags=["6. Repository 模式"])
def repo_create_user(
    user_in: UserCreate,
    repo: UserRepository = Depends(get_user_repo),
):
    """用 Repository 创建用户"""
    if repo.get_by_email(user_in.email):
        raise HTTPException(400, "邮箱已存在")
    return repo.create(
        username=user_in.username,
        email=user_in.email,
        hashed_password="hashed_" + user_in.password,
        balance=1000.0,
    )


@app.get("/repo-demo/users/", response_model=list[UserResponse], tags=["6. Repository 模式"])
def repo_list_users(
    skip: int = 0,
    limit: int = 100,
    repo: UserRepository = Depends(get_user_repo),
):
    """用 Repository 获取用户列表"""
    return repo.get_all(skip=skip, limit=limit)


@app.get("/repo-demo/users/{user_id}", response_model=UserResponse, tags=["6. Repository 模式"])
def repo_get_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
):
    """用 Repository 获取单个用户"""
    user = repo.get_with_posts(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


@app.post("/repo-demo/users/{user_id}/deactivate", tags=["6. Repository 模式"])
def repo_deactivate_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
):
    """用 Repository 专用方法停用用户"""
    user = repo.deactivate(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    return {"message": f"用户 {user.username} 已停用", "is_active": False}


# ── 系统 ──

@app.get("/", tags=["系统"])
def root():
    return {
        "message": "数据库高级话题 Demo",
        "sections": {
            "1. 索引演示": ["/index-demo/users-by-email?email=...", "/index-demo/explain?email=..."],
            "2. 事务演示": ["POST /transaction-demo/transfer", "GET /transaction-demo/users"],
            "3. N+1 演示": ["/n1-demo/posts-lazy (N+1)", "/n1-demo/posts-eager (1 SQL)"],
            "4. 分页演示": ["/products/?page=1&page_size=10", "/products/cursor?cursor=&page_size=10"],
            "5. 软删除演示": ["DELETE /products/{id}", "POST /products/{id}/restore"],
            "6. Repository 模式": ["/repo-demo/users/"],
        },
        "tip": "把 echo=False 改为 echo=True 观察 SQL 执行",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
