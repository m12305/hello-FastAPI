"""
2.3 依赖注入（Dependency Injection）— 可运行 Demo

启动方式:
    cd 阶段2-请求与响应/code/2.3-依赖注入
    uvicorn main:app --reload

访问 http://127.0.0.1:8000/docs 交互式测试。

测试命令:
    # ─── 基本依赖注入 ───
    curl "http://127.0.0.1:8000/items/?q=phone&page=1"

    # ─── 类依赖（分页） ───
    curl "http://127.0.0.1:8000/users/?page=2&page-size=10"

    # ─── yield 依赖（模拟数据库） ───
    curl "http://127.0.0.1:8000/data"
    # 观察服务器控制台输出：打开连接 → 查询 → 关闭连接

    # ─── 嵌套依赖（API Key → 用户 → 权限） ───
    curl -H "X-API-Key: key-admin-123" http://127.0.0.1:8000/admin/stats
    curl -H "X-API-Key: key-editor-456" http://127.0.0.1:8000/editor/posts
    curl -H "X-API-Key: key-user-789" http://127.0.0.1:8000/admin/stats        # 403
    curl -H "X-API-Key: bad-key" http://127.0.0.1:8000/admin/stats              # 401
    curl http://127.0.0.1:8000/admin/stats                                       # 401（无头）

    # ─── 装饰器级依赖（不需要返回值） ───
    curl http://127.0.0.1:8000/public/items
    curl -H "X-API-Key: key-admin-123" http://127.0.0.1:8000/public/items

    # ─── use_cache=False ───
    curl http://127.0.0.1:8000/ids
"""

import random
import time
from enum import Enum

from fastapi import (
    FastAPI, Depends, Query, Header, HTTPException, Request
)

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="2.3 依赖注入 Demo",
    description=(
        "演示 Depends()、yield 依赖、嵌套依赖、工厂函数、"
        "装饰器级依赖、use_cache 等核心模式"
    ),
    version="1.0.0",
)

# ═══════════════════════════════════════════════════════════
# 模拟数据
# ═══════════════════════════════════════════════════════════
FAKE_USERS = {
    "key-admin-123":  {"id": 1, "name": "Admin",  "role": "admin",  "email": "admin@example.com"},
    "key-editor-456": {"id": 2, "name": "Editor", "role": "editor", "email": "editor@example.com"},
    "key-user-789":   {"id": 3, "name": "Alice",  "role": "user",   "email": "alice@example.com"},
    "key-user-101":   {"id": 4, "name": "Bob",    "role": "user",   "email": "bob@example.com"},
}

FAKE_DB = {
    "items": [
        {"id": 1, "name": "Python FastAPI 入门", "price": 49.9},
        {"id": 2, "name": "Vue.js 实战", "price": 59.9},
        {"id": 3, "name": "Docker DevOps", "price": 79.9},
        {"id": 4, "name": "Redis 深度揭秘", "price": 39.9},
        {"id": 5, "name": "Kubernetes 指南", "price": 89.9},
    ],
    "stats": {"total_users": 1250, "total_orders": 890, "revenue": 124500.50},
}


# ═══════════════════════════════════════════════════════════
# 1. 基本函数依赖 — 分页参数
# ═══════════════════════════════════════════════════════════

def common_parameters(
    q: str | None = Query(default=None, min_length=2, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(
        default=20, ge=1, le=100, alias="page-size", description="每页条数"
    ),
):
    """普通函数作为依赖——返回分页参数的字典"""
    return {
        "q": q,
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
    }


@app.get("/items/", tags=["1. 基本依赖"])
async def list_items(params: dict = Depends(common_parameters)):
    """使用基本函数依赖获取分页参数"""
    # 根据参数做"数据库查询"（这里只是模拟）
    all_items = FAKE_DB["items"]
    if params["q"]:
        all_items = [i for i in all_items if params["q"].lower() in i["name"].lower()]
    paginated = all_items[params["offset"]:params["offset"] + params["page_size"]]
    return {"params": params, "results": paginated, "total": len(all_items)}


# ═══════════════════════════════════════════════════════════
# 2. 类作为依赖（无 __call__）
# ═══════════════════════════════════════════════════════════

class PaginationParams:
    """类作为依赖——FastAPI 自动实例化"""
    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(
            default=20, ge=1, le=50, alias="page-size", description="每页条数"
        ),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@app.get("/users/", tags=["2. 类依赖"])
async def list_users(paging: PaginationParams = Depends()):
    """使用类作为依赖——自动实例化并填充参数"""
    return {
        "page": paging.page,
        "page_size": paging.page_size,
        "offset": paging.offset,
        "users": list(FAKE_USERS.values())[paging.offset:paging.offset + paging.page_size],
    }


# ═══════════════════════════════════════════════════════════
# 3. yield 依赖 — 模拟数据库会话
# ═══════════════════════════════════════════════════════════

class FakeDBSession:
    """模拟数据库会话"""
    def __init__(self):
        self.id = id(self) % 10000
        print(f"  🔗 [Session #{self.id}] 数据库连接已打开")

    def query(self, table: str):
        print(f"  📖 [Session #{self.id}] 执行查询: SELECT * FROM {table}")
        return FAKE_DB.get(table, [])

    def close(self):
        print(f"  🔒 [Session #{self.id}] 数据库连接已关闭")


async def get_db():
    """yield 依赖——管理数据库会话的生命周期"""
    db = FakeDBSession()
    try:
        yield db  # 把会话传给端点函数
    finally:
        db.close()  # 响应返回后执行，保证连接被关闭


@app.get("/data", tags=["3. yield 依赖"])
async def read_data(db: FakeDBSession = Depends(get_db)):
    """使用 yield 依赖获取数据库会话——观察控制台看到连接打开和关闭"""
    items = db.query("items")
    stats = db.query("stats")
    return {"items": items, "stats": stats}
    # 返回后，yield 之后的 close() 自动执行


# ═══════════════════════════════════════════════════════════
# 4. 嵌套依赖链 — API Key → 用户 → 权限
# ═══════════════════════════════════════════════════════════

# 第一层：从请求头提取 API Key
async def get_api_key(x_api_key: str = Header(alias="X-API-Key")):
    """提取 API Key——如果没有提供则拒绝"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")
    return x_api_key


# 第二层：用 API Key 查找用户
async def get_current_user(
    api_key: str = Depends(get_api_key),  # ← 依赖第一层
):
    """通过 API Key 查找对应的用户"""
    user = FAKE_USERS.get(api_key)
    if not user:
        raise HTTPException(
            status_code=401,
            detail=f"无效的 API Key。有效 Key: {', '.join(FAKE_USERS.keys())}",
        )
    return user


# 第三层：权限校验（工厂函数）
class Role(str, Enum):
    admin = "admin"
    editor = "editor"
    user = "user"


def require_role(role: Role):
    """工厂函数——传入角色，返回该角色的校验依赖"""
    async def role_checker(
        current_user: dict = Depends(get_current_user),  # ← 依赖第二层
    ):
        if current_user["role"] != role:
            raise HTTPException(
                status_code=403,
                detail=f"权限不足：需要 {role} 角色，你当前是 {current_user['role']}",
            )
        return current_user
    return role_checker


@app.get("/users/me", tags=["4. 嵌套依赖"])
async def read_current_user(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息——需要有效 API Key"""
    return {"message": "认证成功", "user": current_user}


@app.get("/admin/stats", tags=["4. 嵌套依赖"])
async def admin_stats(
    admin: dict = Depends(require_role(Role.admin)),  # ← 工厂函数生成的依赖
):
    """管理员数据面板——仅 admin 角色可访问"""
    return {
        "message": f"管理员 {admin['name']} 的数据面板",
        "stats": FAKE_DB["stats"],
    }


@app.get("/editor/posts", tags=["4. 嵌套依赖"])
async def editor_posts(
    editor: dict = Depends(require_role(Role.editor)),
):
    """编辑者面板——仅 editor 角色可访问"""
    return {
        "message": f"编辑者 {editor['name']} 的文章列表",
        "posts": [{"id": 1, "title": "草稿：FastAPI 进阶"}],
    }


# ═══════════════════════════════════════════════════════════
# 5. 装饰器级依赖 — 不需要返回值
# ═══════════════════════════════════════════════════════════

async def verify_api_key_header(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """装饰器级依赖——只做检查，不返回数据"""
    print(f"  🔑 [中间件级依赖] API Key 已验证: {x_api_key or '未提供'}")
    # 这里不做强制校验，只记录日志
    # 如果要做强制校验，抛出 HTTPException 即可


@app.get(
    "/public/items",
    tags=["5. 装饰器级依赖"],
    dependencies=[Depends(verify_api_key_header)],  # ← 装饰器上使用依赖
)
async def public_items():
    """公开接口——依赖只记录日志，不返回数据"""
    return {"items": FAKE_DB["items"]}


# ═══════════════════════════════════════════════════════════
# 6. use_cache 演示
# ═══════════════════════════════════════════════════════════

# 用于演示缓存的计数器
_cache_counter = 0


def expensive_operation():
    """模拟一个耗时/有副作用的操作——默认会被缓存"""
    global _cache_counter
    _cache_counter += 1
    print(f"  💸 [expensive_operation] 执行第 {_cache_counter} 次")
    return {"computed": True, "attempt": _cache_counter}


def random_id_generator():
    """每次调用生成不同的随机 ID——适合 use_cache=False"""
    return {"random_id": f"req-{random.randint(1000, 9999)}"}


@app.get("/cache-demo", tags=["6. use_cache"])
async def cache_demo(
    expensive: dict = Depends(expensive_operation),
    expensive2: dict = Depends(expensive_operation),  # ← 会被缓存，不重复执行
):
    """演示依赖缓存——expensive_operation 只执行一次"""
    return {
        "expensive": expensive,
        "expensive2": expensive2,
        "cached": expensive is expensive2,  # True — 同一个对象
        "note": "查看控制台，expensive_operation 只执行了一次",
    }


@app.get("/no-cache-demo", tags=["6. use_cache"])
async def no_cache_demo(
    id1: dict = Depends(random_id_generator, use_cache=False),
    id2: dict = Depends(random_id_generator, use_cache=False),
):
    """演示 use_cache=False——每次调用都重新执行"""
    return {
        "id1": id1,
        "id2": id2,
        "different": id1 != id2,  # True — 不同的值
        "note": "use_cache=False 确保每次调用都重新执行",
    }


# ═══════════════════════════════════════════════════════════
# 7. yield 依赖 — 请求计时日志
# ═══════════════════════════════════════════════════════════

async def log_request_timing(request: Request):
    """yield 依赖——记录每个请求的耗时"""
    start = time.perf_counter()
    print(f"\n  ⏱  [{request.method}] {request.url.path} 开始处理...")
    yield  # 等待端点执行
    elapsed = (time.perf_counter() - start) * 1000
    print(f"  ⏱  [{request.method}] {request.url.path} 完成，耗时 {elapsed:.2f}ms")


@app.get("/timing-demo", tags=["7. yield 日志"])
async def timing_demo(
    _log=Depends(log_request_timing),
):
    """演示 yield 依赖做请求计时——查看控制台输出"""
    time.sleep(0.1)  # 模拟业务处理
    return {"message": "计时演示——请查看控制台输出"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
