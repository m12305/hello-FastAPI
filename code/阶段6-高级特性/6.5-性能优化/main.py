"""
6.5 性能优化 — 可运行 Demo

运行方式:
    cd code/阶段6-高级特性/6.5-性能优化
    pip install fastapi uvicorn[standard] sqlalchemy aiosqlite httpx
    uvicorn main:app --reload
    浏览器打开 http://127.0.0.1:8000/docs

本 Demo 涵盖:
  1. N+1 查询问题 vs joinedload 解决方案（直观对比 SQL 条数）
  2. 索引的价值（加索引前后的查询性能）
  3. 同步 def vs 异步 async def 对比
  4. GZip 压缩效果
  5. 响应时间监控中间件（X-Process-Time）
  6. 分页 vs 全量查询
"""

import time
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, Response, Query
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import (
    create_engine, String, Integer, DateTime, ForeignKey, Index,
    select, func, text,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, Session, sessionmaker,
    relationship, joinedload, selectinload,
)

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="6.5 性能优化 Demo",
    description="对比：N+1 修复 / 索引 / sync vs async / GZip / 分页",
    version="1.0.0",
)

# ── 1. GZip 中间件（压缩 >1000 字节的响应）──
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── 2. 响应计时中间件 ──
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    """给每个响应加上 X-Process-Time 头"""
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    response.headers["X-Process-Time"] = f"{elapsed:.2f}ms"
    return response


# ═══════════════════════════════════════════════════════════
# 数据库设置（SQLite + ORM）
# ═══════════════════════════════════════════════════════════

engine = create_engine(
    "sqlite:///./perf_demo.db",
    connect_args={"check_same_thread": False},
    echo=False,  # ← 设为 True 可看到所有 SQL
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Author(Base):
    """作者（有索引 vs 无索引的对比）"""
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)       # ← 有索引
    email: Mapped[str] = mapped_column(String(100))                 # ← 无索引（演示用）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    """书"""
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), index=True)

    author: Mapped["Author"] = relationship(back_populates="books")


# ── 建表 + 种子数据 ──
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _seed_data()


def _seed_data():
    """生成测试数据：100 个作者 × 每人 5 本书 = 500 本书"""
    db = SessionLocal()
    try:
        if db.query(Author).count() > 0:
            return  # 已有数据

        print("🌱 正在生成种子数据（100 位作者 × 5 本书 = 500 条记录）...")
        authors = []
        for i in range(1, 101):
            author = Author(
                name=f"作者_{i:03d}",
                email=f"author{i:03d}@example.com",
            )
            authors.append(author)
        db.add_all(authors)
        db.flush()

        books = []
        for author in authors:
            for j in range(1, 6):
                books.append(Book(
                    title=f"{author.name}的第{j}本书",
                    author_id=author.id,
                ))
        db.add_all(books)
        db.commit()
        print(f"✅ 种子数据已就绪: {len(authors)} 位作者, {len(books)} 本书")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 演示 1：N+1 问题 vs joinedload（5.2 的核心演示）
# ═══════════════════════════════════════════════════════════

@app.get("/demo/n-plus-one")
def demo_n_plus_one():
    """
    ❌ N+1 查询问题演示。

    查询 100 本书 + 每本书的作者 → 1 + 100 = 101 条 SQL！
    观察终端输出的 SQL 条数（如果把 engine echo=True）。
    """
    db = SessionLocal()
    try:
        start = time.time()
        books = db.query(Book).limit(100).all()  # 第 1 条 SQL: SELECT books

        # N+1 发生在这里：每本书的 .author 触发一条新 SQL
        result = [
            {"id": b.id, "title": b.title, "author": b.author.name}
            #                        ↑ 每次访问 b.author 都会发一条 SQL！
            for b in books
        ]
        elapsed = (time.time() - start) * 1000

        return {
            "mode": "❌ N+1 查询（Lazy Loading）",
            "sql_count": f"1 + {len(books)} = {1 + len(books)} 条 SQL",
            "time_ms": f"{elapsed:.2f}",
            "data": result[:5],  # 只展示前 5 条
            "hint": "换成 GET /demo/joinedload 看看差异",
        }
    finally:
        db.close()


@app.get("/demo/joinedload")
def demo_joinedload():
    """
    ✅ 用 joinedload 一次性 JOIN 查询。

    同样查 100 本书 + 作者 → 只需 1 条 SQL！
    观察 X-Process-Time 头的差异。
    """
    db = SessionLocal()
    try:
        start = time.time()
        books = (
            db.query(Book)
            .options(joinedload(Book.author))  # ← 关键！JOIN authors
            .limit(100)
            .all()
        )
        # 这里访问 b.author.name 不会再发 SQL
        result = [
            {"id": b.id, "title": b.title, "author": b.author.name}
            for b in books
        ]
        elapsed = (time.time() - start) * 1000

        return {
            "mode": "✅ joinedload（Eager Loading）",
            "sql_count": "1 条 SQL（JOIN）",
            "time_ms": f"{elapsed:.2f}",
            "data": result[:5],
            "hint": "对比 GET /demo/n-plus-one 的耗时和 SQL 条数",
        }
    finally:
        db.close()


@app.get("/demo/selectinload")
def demo_selectinload():
    """
    ✅ 用 selectinload：2 条 SQL 解决（先查书，再 IN 查作者）。

    适合一对多、数据量大的场景（避免 JOIN 产生笛卡尔积）。
    """
    db = SessionLocal()
    try:
        start = time.time()
        books = (
            db.query(Book)
            .options(selectinload(Book.author))  # ← 2 条 SQL
            .limit(100)
            .all()
        )
        result = [
            {"id": b.id, "title": b.title, "author": b.author.name}
            for b in books
        ]
        elapsed = (time.time() - start) * 1000

        return {
            "mode": "✅ selectinload（2 条 SQL）",
            "sql_count": "2 条 SQL",
            "time_ms": f"{elapsed:.2f}",
            "data": result[:5],
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 演示 2：索引的价值
# ═══════════════════════════════════════════════════════════

@app.get("/demo/index-comparison")
def demo_index_comparison():
    """
    对比：有索引 vs 无索引的查询。

    Author.name 有 index=True，Author.email 没有索引。
    在大数据量下，有索引的查询快 10-100 倍。
    """
    db = SessionLocal()
    try:
        # 查有索引的 name 列
        start = time.time()
        db.query(Author).filter(Author.name == "作者_050").all()
        indexed_time = (time.time() - start) * 1000

        # 查没有索引的 email 列
        start = time.time()
        db.query(Author).filter(Author.email == "author050@example.com").all()
        no_index_time = (time.time() - start) * 1000

        return {
            "有索引 (name)": {"time_ms": f"{indexed_time:.4f}", "column": "name", "indexed": True},
            "无索引 (email)": {"time_ms": f"{no_index_time:.4f}", "column": "email", "indexed": False},
            "hint": "在大表（百万行）上，索引差距会达到 100 倍以上",
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 演示 3：同步 vs 异步对比
# ═══════════════════════════════════════════════════════════

def blocking_io_work() -> str:
    """模拟同步阻塞 IO（如 requests.get）"""
    time.sleep(0.1)  # 模拟 100ms 的 IO 等待
    return "sync_done"


async def async_io_work() -> str:
    """模拟异步 IO（如 httpx.AsyncClient.get）"""
    await asyncio.sleep(0.1)  # 不阻塞事件循环
    return "async_done"


@app.get("/demo/sync-endpoint")
def sync_endpoint():
    """
    同步 def 端点 —— FastAPI 在线程池中执行。

    单个请求耗时 = 100ms。但如果并发 10 个请求，
    每个都在独立线程，总耗时大约相同。
    """
    start = time.time()
    result = blocking_io_work()
    elapsed = (time.time() - start) * 1000
    return {"mode": "同步 def（线程池）", "result": result, "time_ms": f"{elapsed:.2f}"}


@app.get("/demo/async-endpoint")
async def async_endpoint():
    """
    异步 async def 端点 —— 在事件循环中执行。

    单个请求耗时 = 100ms。并发 10 个请求时，
    事件循环可以在等待 IO 期间处理其他请求。
    """
    start = time.time()
    result = await async_io_work()
    elapsed = (time.time() - start) * 1000
    return {"mode": "异步 async def（事件循环）", "result": result, "time_ms": f"{elapsed:.2f}"}


# ═══════════════════════════════════════════════════════════
# 演示 4：分页 vs 全量查询
# ═══════════════════════════════════════════════════════════

@app.get("/demo/pagination-comparison")
def demo_pagination_comparison():
    """
    分页 vs 全量查询的响应大小对比。

    全量返回 500 条 → 响应体巨大，序列化慢。
    分页只返回 10 条 → 响应体小，速度快。
    """
    db = SessionLocal()
    try:
        # 全量查询
        start = time.time()
        all_books = db.query(Book).options(joinedload(Book.author)).all()
        all_time = (time.time() - start) * 1000
        all_count = len(all_books)

        # 分页查询（只取 10 条）
        start = time.time()
        paged_books = db.query(Book).options(joinedload(Book.author)).limit(10).all()
        page_time = (time.time() - start) * 1000
        page_count = len(paged_books)

        return {
            "全量查询": {"count": all_count, "time_ms": f"{all_time:.2f}", "说明": "传输所有数据"},
            "分页查询": {"count": page_count, "time_ms": f"{page_time:.2f}", "说明": "只传输第 1 页"},
            "建议": "列表接口务必加分页！page + size",
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# 演示 5：GZip 效果
# ═══════════════════════════════════════════════════════════

@app.get("/demo/gzip-demo")
def demo_gzip():
    """
    返回大量重复数据——GZip 压缩效果明显。

    观察响应头：
      Content-Encoding: gzip  ← 自动压缩
    检查 Body 大小：原始几 KB → 压缩后几百字节
    """
    # 返回 200 条相似数据（GZip 最喜欢重复内容）
    return {
        "data": [
            {
                "id": i,
                "title": f"这是第{i}条数据，包含一些重复的文本内容来展示 GZip 压缩效果",
                "description": "GZip 对文本内容的压缩率很高，尤其是 HTML/JSON 等重复结构多的内容。"
            }
            for i in range(200)
        ]
    }


# ═══════════════════════════════════════════════════════════
# 首页：性能优化对比汇总
# ═══════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "title": "性能优化 Demo",
        "demos": {
            "N+1 问题": {
                "❌ N+1": "GET /demo/n-plus-one",
                "✅ joinedload": "GET /demo/joinedload",
                "✅ selectinload": "GET /demo/selectinload",
                "说明": "对比 SQL 条数和耗时",
            },
            "索引": {
                "对比": "GET /demo/index-comparison",
                "说明": "有索引 vs 无索引的查询速度",
            },
            "sync vs async": {
                "同步": "GET /demo/sync-endpoint",
                "异步": "GET /demo/async-endpoint",
                "说明": "对比两种定义方式的 IO 处理",
            },
            "分页": {
                "对比": "GET /demo/pagination-comparison",
                "说明": "全量 vs 分页的响应大小和速度",
            },
            "GZip": {
                "演示": "GET /demo/gzip-demo",
                "说明": "查看 Content-Encoding: gzip 头",
            },
        },
        "hint": "所有端口的响应头中都有 X-Process-Time（ms），对比观察！",
    }


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  6.5 性能优化 Demo")
    print("  http://127.0.0.1:8000/docs")
    print("=" * 60)
    print()
    print("💡 测试提示:")
    print("  1. 对比 GET /demo/n-plus-one 和 /demo/joinedload 的耗时")
    print("  2. GET /demo/index-comparison → 看索引差距")
    print("  3. 打开浏览器 DevTools → Network → 对比响应头")
    print("     - X-Process-Time: 处理耗时（ms）")
    print("     - Content-Encoding: gzip (如果有)")
    print("  4. 观察 GZip 响应的 Content-Length（压缩后大小）")
    print("  5. 所有端点都返回详细的数据和对比信息")
    print()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
