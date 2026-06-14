"""
6.3 事件钩子与生命周期 — 可运行 Demo

运行方式:
    cd code/阶段6-高级特性/6.3-事件钩子与生命周期
    pip install fastapi uvicorn[standard]
    uvicorn main:app --reload
    浏览器打开 http://127.0.0.1:8000/docs

本 Demo 涵盖:
  1. lifespan 上下文管理器（替代 on_event）
  2. 在启动时初始化"数据库连接池"和"Redis 客户端"（模拟）
  3. 通过 app.state 在请求中访问这些资源
  4. 健康检查端点 /health
  5. 优雅关闭：释放所有资源
  6. 后台任务的启停管理

对比: 本 Demo 使用 lifespan 而非 @app.on_event()
      查看终端输出可以看到完整的"启动 → 存活 → 关闭"生命周期日志。
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════
# 模拟外部资源（实际项目用真实的 DB / Redis）
# ═══════════════════════════════════════════════════════════

class FakeDatabase:
    """模拟数据库连接池"""

    def __init__(self):
        self.connected = False
        self.pool_size = 0

    async def connect(self, pool_size: int = 10):
        print(f"  🔌 正在创建数据库连接池 (size={pool_size})...")
        await asyncio.sleep(0.3)  # 模拟连接耗时
        self.connected = True
        self.pool_size = pool_size
        print(f"  ✅ 数据库连接池已就绪 (size={pool_size})")

    async def disconnect(self):
        print(f"  🔌 正在释放数据库连接池...")
        await asyncio.sleep(0.2)
        self.connected = False
        print(f"  ✅ 数据库连接池已释放")

    async def query(self, sql: str) -> str:
        if not self.connected:
            raise RuntimeError("数据库未连接")
        # 模拟查询
        await asyncio.sleep(0.01)
        return f"[模拟结果] SQL: {sql[:50]}..."


class FakeRedis:
    """模拟 Redis 客户端"""

    def __init__(self):
        self.connected = False
        self._cache: dict[str, str] = {}

    async def connect(self):
        print(f"  🔴 正在连接 Redis...")
        await asyncio.sleep(0.2)
        self.connected = True
        print(f"  ✅ Redis 已就绪")

    async def disconnect(self):
        print(f"  🔴 正在断开 Redis...")
        await asyncio.sleep(0.1)
        self.connected = False
        print(f"  ✅ Redis 已断开")

    async def get(self, key: str) -> str | None:
        return self._cache.get(key)

    async def set(self, key: str, value: str):
        self._cache[key] = value


# ═══════════════════════════════════════════════════════════
# lifespan 上下文管理器
# ═══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器。

    ┌─ yield 之前 = startup ─────────────────────┐
    │  初始化 DB、Redis、加载模型、启动后台任务  │
    ├─ yield 期间 = 应用存活，处理请求 ──────────┤
    ├─ yield 之后 = shutdown ────────────────────┤
    │  取消后台任务、释放连接、清理资源          │
    └───────────────────────────────────────────┘
    """
    print("\n" + "=" * 60)
    print("  🚀 应用启动中...")
    print("=" * 60)

    # ═══ 启动阶段 ═══
    # 1. 初始化数据库
    db = FakeDatabase()
    await db.connect(pool_size=20)
    app.state.db = db  # ← 存在 app.state 上，所有请求都能访问

    # 2. 初始化 Redis
    redis = FakeRedis()
    await redis.connect()
    app.state.redis = redis

    # 3. 启动一个后台任务（如定时清理、消费队列）
    app.state.background_task = asyncio.create_task(
        _periodic_health_check(app)
    )

    # 4. 记录启动时间
    app.state.started_at = datetime.now()

    print(f"\n  ✅ 所有资源初始化完成！应用已就绪。")
    print("=" * 60 + "\n")

    # ═══ 把控制权交给应用 ═══
    yield

    # ═══ 关闭阶段 ═══
    print("\n" + "=" * 60)
    print("  👋 应用正在关闭...")
    print("=" * 60)

    # 1. 取消后台任务
    app.state.background_task.cancel()
    try:
        await app.state.background_task
    except asyncio.CancelledError:
        print("  ✅ 后台任务已取消")

    # 2. 释放资源（注意顺序：先关外部的，再关内部的）
    if hasattr(app.state, "redis"):
        await app.state.redis.disconnect()
    if hasattr(app.state, "db"):
        await app.state.db.disconnect()

    print("  ✅ 所有资源已释放。再见！")
    print("=" * 60 + "\n")


async def _periodic_health_check(app: FastAPI):
    """
    后台任务：每 30 秒记录一次健康信息。

    在生产环境中，这可能是：
      - 定期清理过期 Token
      - 同步配置
      - 收集指标
    """
    tick = 0
    while True:
        try:
            await asyncio.sleep(30)
            tick += 1
            db_ok = app.state.db.connected
            redis_ok = app.state.redis.connected
            print(f"  🩺 [健康检查 #{tick}] DB: {'✅' if db_ok else '❌'}, Redis: {'✅' if redis_ok else '❌'}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"  ⚠️ [健康检查] 出错: {e}")


# ═══════════════════════════════════════════════════════════
# 创建应用（传入 lifespan）
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="6.3 生命周期 Demo",
    description="学习 lifespan 管理应用启动/关闭的完整示例",
    version="1.0.0",
    lifespan=lifespan,  # ← 关键！传入 lifespan
)


# ═══════════════════════════════════════════════════════════
# 依赖注入：从 app.state 获取资源
# ═══════════════════════════════════════════════════════════

def get_db(request: Request) -> FakeDatabase:
    """从 app.state 中获取数据库"""
    db = request.app.state.db
    if not db or not db.connected:
        raise HTTPException(503, "数据库不可用")
    return db


def get_redis(request: Request) -> FakeRedis:
    """从 app.state 中获取 Redis"""
    redis = request.app.state.redis
    if not redis or not redis.connected:
        raise HTTPException(503, "Redis 不可用")
    return redis


# ═══════════════════════════════════════════════════════════
# 端点
# ═══════════════════════════════════════════════════════════

@app.get("/")
def root():
    """首页：展示应用信息"""
    return {
        "message": "生命周期管理 Demo",
        "feature": "使用 lifespan 管理应用启停",
        "endpoints": {
            "GET /health": "健康检查（检查 DB + Redis）",
            "GET /info": "应用状态信息",
            "GET /db-test": "测试数据库查询",
            "GET /redis-test": "测试 Redis 读写",
        },
    }


@app.get("/health")
async def health(request: Request):
    """
    健康检查 —— K8s / 负载均衡用。

    返回 200 表示健康，503 表示不健康。
    生产环境请检查真实 DB/Redis 连接。
    """
    checks = {
        "db": request.app.state.db.connected if hasattr(request.app.state, "db") else False,
        "redis": request.app.state.redis.connected if hasattr(request.app.state, "redis") else False,
    }
    all_ok = all(checks.values())
    return {
        "status": "healthy" if all_ok else "unhealthy",
        "checks": checks,
        "started_at": str(request.app.state.started_at) if hasattr(request.app.state, "started_at") else "unknown",
    }


@app.get("/info")
def info(request: Request):
    """应用状态信息"""
    return {
        "app_version": "1.0.0",
        "started_at": str(request.app.state.started_at) if hasattr(request.app.state, "started_at") else "unknown",
        "db_pool_size": request.app.state.db.pool_size if hasattr(request.app.state, "db") else 0,
        "redis_connected": request.app.state.redis.connected if hasattr(request.app.state, "redis") else False,
        "uptime_seconds": (
            (datetime.now() - request.app.state.started_at).total_seconds()
            if hasattr(request.app.state, "started_at")
            else 0
        ),
    }


@app.get("/db-test")
async def db_test(db: FakeDatabase = Depends(get_db)):
    """测试数据库查询"""
    result = await db.query("SELECT * FROM users WHERE is_active = 1")
    return {"query_result": result, "db_connected": db.connected}


class CacheData(BaseModel):
    key: str
    value: str


@app.post("/redis-test")
async def redis_set(data: CacheData, redis: FakeRedis = Depends(get_redis)):
    """测试 Redis 写入"""
    await redis.set(data.key, data.value)
    return {"message": f"已缓存 {data.key} = {data.value}"}


@app.get("/redis-test/{key}")
async def redis_get(key: str, redis: FakeRedis = Depends(get_redis)):
    """测试 Redis 读取"""
    value = await redis.get(key)
    if value is None:
        raise HTTPException(404, f"Key '{key}' 不存在")
    return {"key": key, "value": value}


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  6.3 生命周期 Demo")
    print("  http://127.0.0.1:8000/docs")
    print("=" * 60)
    print()
    print("💡 测试提示:")
    print("  1. 观察启动时的终端输出（DB + Redis 初始化）")
    print("  2. GET /health → 查看健康状态")
    print("  3. GET /info → 查看启动时间和资源状态")
    print("  4. POST /redis-test → 写入缓存")
    print("  5. GET /redis-test/{key} → 读取缓存")
    print("  6. 按 Ctrl+C 关闭 → 观察优雅关闭的终端输出")
    print()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
