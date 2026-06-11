"""
2.4 中间件与 CORS — 可运行 Demo

启动方式:
    cd 阶段2-请求与响应/code/2.4-中间件CORS
    uvicorn main:app --reload

访问 http://127.0.0.1:8000/docs 交互式测试。

测试命令:
    # ─── 请求 ID 和计时 — 查看响应头 ───
    curl -i http://127.0.0.1:8000/
    # 会看到响应头中有 X-Request-ID 和 X-Process-Time

    # ─── 自定义请求 ID ───
    curl -i -H "X-Request-ID: my-custom-id" http://127.0.0.1:8000/
    # 响应头中 X-Request-ID = my-custom-id

    # ─── 维护模式 ───
    curl -i -H "X-Maintenance: true" http://127.0.0.1:8000/
    # 返回 503 Service Unavailable

    # ─── 恶意 User-Agent 拦截 ───
    curl -i -H "User-Agent: sqlmap/1.0" http://127.0.0.1:8000/
    # 返回 403 Forbidden

    # ─── 触发异常 — 测试全局异常中间件 ───
    curl -i http://127.0.0.1:8000/trigger-error
    # 返回统一错误格式，状态码 500

    # ─── 限流测试 — 快速发多次请求 ───
    for i in {1..35}; do curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/; done
    # 前 30 次返回 200，后面返回 429 Too Many Requests

    # ─── GET /debug — 查看 request.state 中的数据 ───
    curl http://127.0.0.1:8000/debug
"""

import json
import logging
import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ═══════════════════════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("api")

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="2.4 中间件与 CORS Demo",
    description=(
        "演示自定义中间件（请求ID、计时、维护模式、日志、限流、异常捕获）"
        "和 CORS 配置"
    ),
    version="1.0.0",
)

# ═══════════════════════════════════════════════════════════
# 0. CORS 中间件 — 必须最先添加（最外层）
# ═══════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
    max_age=3600,
)

# ═══════════════════════════════════════════════════════════
# 全局异常捕获中间件（第 1 层）
# ═══════════════════════════════════════════════════════════
@app.middleware("http")
async def exception_handler_middleware(request: Request, call_next):
    """捕获所有未处理的异常，返回统一错误格式

    这个中间件包裹了所有后续中间件和路由——
    任何未捕获的异常都会在这里被转换为友好的 JSON 响应。
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"未处理异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "服务器内部错误，请稍后重试",
                "code": "INTERNAL_ERROR",
                "path": request.url.path,
            },
        )

# ═══════════════════════════════════════════════════════════
# 请求 ID 中间件（第 2 层）
# ═══════════════════════════════════════════════════════════
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """为每个请求生成唯一 ID

    优先级：客户端 X-Request-ID > 自动生成 UUID
    这个 ID 会：
    1. 注入到 request.state（路由中可读取）
    2. 添加到响应头（前端可追踪）
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ═══════════════════════════════════════════════════════════
# 维护模式中间件（第 3 层）
# ═══════════════════════════════════════════════════════════
@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    """如果请求头 X-Maintenance: true，返回 503

    这在生产环境中很有用——可以在不重启服务的情况下
    通过 Nginx 或网关设置这个请求头来启用维护模式。
    """
    if request.headers.get("X-Maintenance", "").lower() == "true":
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service Unavailable",
                "detail": "系统维护中，请稍后再试",
                "code": "MAINTENANCE",
            },
        )
    return await call_next(request)

# ═══════════════════════════════════════════════════════════
# 恶意 User-Agent 拦截中间件（第 4 层）
# ═══════════════════════════════════════════════════════════
@app.middleware("http")
async def block_bad_agents_middleware(request: Request, call_next):
    """拦截已知的恶意 User-Agent"""
    user_agent = request.headers.get("User-Agent", "").lower()
    blocked_keywords = [
        "sqlmap", "nikto", "nmap", "acunetix",
        "burpsuite", "hydra", "masscan",
    ]
    if any(kw in user_agent for kw in blocked_keywords):
        logger.warning(f"拦截恶意 UA: {user_agent[:80]}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden: suspicious user agent detected"},
        )
    return await call_next(request)

# ═══════════════════════════════════════════════════════════
# 请求限流中间件（第 5 层）
# ═══════════════════════════════════════════════════════════
class SimpleRateLimiter:
    """简易内存限流器——生产环境应替换为 Redis 实现"""
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.history: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # 清理过期的记录
        self.history[client_ip] = [
            t for t in self.history[client_ip]
            if now - t < self.window
        ]
        if len(self.history[client_ip]) >= self.max_requests:
            return False
        self.history[client_ip].append(now)
        return True


limiter = SimpleRateLimiter(max_requests=30, window_seconds=60)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """限流：同一 IP 每分钟最多 30 次请求"""
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "请求过于频繁，请稍后再试",
                "retry_after_seconds": 60,
            },
        )
    return await call_next(request)

# ═══════════════════════════════════════════════════════════
# 请求/响应计时 + 结构化日志中间件（第 6 层 — 最内层）
# ═══════════════════════════════════════════════════════════
@app.middleware("http")
async def logging_timing_middleware(request: Request, call_next):
    """记录请求日志和耗时——最内层中间件，记录真实业务耗时"""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    # 添加响应头
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

    # 结构化日志
    log_entry = json.dumps({
        "request_id": getattr(request.state, "request_id", "-"),
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown",
        "status": response.status_code,
        "duration_ms": round(duration_ms, 2),
    }, ensure_ascii=False)
    logger.info(log_entry)

    return response

# ═══════════════════════════════════════════════════════════
# 路由 — 业务端点
# ═══════════════════════════════════════════════════════════

@app.get("/", tags=["基础端点"])
async def root(request: Request):
    """首页——所有中间件都会对这次请求生效"""
    return {
        "message": "Hello from 2.4 中间件 Demo",
        "request_id": getattr(request.state, "request_id", "unknown"),
        "hint": "查看响应头中的 X-Request-ID 和 X-Process-Time",
    }


@app.get("/debug", tags=["基础端点"])
async def debug(request: Request):
    """调试端点——返回 request.state 中中间件注入的数据"""
    return {
        "request_id": getattr(request.state, "request_id", "not set"),
        "client_ip": request.client.host if request.client else "unknown",
        "note": "这些数据是由 request_id_middleware 注入到 request.state 中的",
    }


@app.get("/trigger-error", tags=["基础端点"])
async def trigger_error():
    """故意抛出异常——测试全局异常中间件"""
    logger.warning("有人触发了 /trigger-error 测试端点")
    raise ValueError("这是一个故意抛出的异常，用于测试全局异常捕获中间件")


@app.get("/slow", tags=["基础端点"])
async def slow_endpoint():
    """慢接口——测试耗时记录"""
    time.sleep(0.3)
    return {"message": "这个接口故意慢了 0.3 秒——查看 X-Process-Time 响应头"}


@app.get("/ping", tags=["基础端点"])
async def ping():
    """健康检查——不受限流影响的好选择（这里演示正常返回）"""
    return {"status": "ok", "service": "2.4-middleware-demo"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
