"""
1.1 Hello World — 第一个 FastAPI 应用

运行方式：
    uvicorn 1.1_hello_world:app --reload

然后访问：
    http://127.0.0.1:8000         → Hello World
    http://127.0.0.1:8000/docs    → Swagger UI 交互式文档
    http://127.0.0.1:8000/redoc   → ReDoc 文档
    http://127.0.0.1:8000/ping    → 健康检查
    http://127.0.0.1:8000/time    → 服务器时间
    http://127.0.0.1:8000/hello/你的名字 → 路径参数测试
"""

from fastapi import FastAPI
from datetime import datetime

# 创建应用实例（带元数据，显示在文档中）
app = FastAPI(
    title="我的第一个 API",
    description="FastAPI 学习项目 — 第一章",
    version="0.1.0",
)


# ===== 最简路由 =====
@app.get("/")
async def root():
    """根路径：返回欢迎信息"""
    return {"message": "Hello World", "framework": "FastAPI"}


# ===== 健康检查 =====
@app.get("/ping")
async def ping():
    """健康检查：运维和监控用"""
    return {"status": "ok"}


# ===== 服务器时间 =====
@app.get("/time")
async def current_time():
    """返回服务器当前时间"""
    return {
        "current_time": datetime.now().isoformat(),
        "timestamp": int(datetime.now().timestamp()),
    }


# ===== 路径参数 =====
@app.get("/hello/{name}")
async def hello(name: str):
    """向指定用户问好（演示路径参数）"""
    return {"message": f"Hello, {name}!", "name": name}


# ===== 启动说明 =====
if __name__ == "__main__":
    import uvicorn
    print("启动服务器：http://127.0.0.1:8000")
    print("交互文档：http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
