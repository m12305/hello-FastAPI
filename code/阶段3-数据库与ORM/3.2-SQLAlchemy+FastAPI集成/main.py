"""
3.2 SQLAlchemy + FastAPI 集成 — 可运行 Demo

启动方式:
    cd code/阶段3-数据库与ORM/3.2-SQLAlchemy+FastAPI集成
    uvicorn main:app --reload

访问 http://127.0.0.1:8000/docs 交互式测试。

项目结构（对照文档第 2 节）:
    main.py              ← FastAPI 应用入口 + 路由注册
    database.py           ← 引擎、会话工厂、Base、get_db 依赖
    models.py             ← SQLAlchemy ORM 模型（表定义）
    schemas.py            ← Pydantic 模型（请求/响应的数据结构）
    crud.py               ← CRUD 操作函数（增删改查的业务逻辑）
    routers/              ← 路由模块（按资源拆分）
        users.py           ← 用户路由
        posts.py           ← 文章路由

关键知识点:
  1. Depends(get_db) 用 yield 管理 Session 生命周期
  2. ConfigDict(from_attributes=True) 让 Pydantic 能读取 ORM 对象
  3. joinedload() 解决 N+1 查询问题
  4. 数据模型 (models) 和 API 模型 (schemas) 必须分离

curl 测试:
    # ─── 用户 ───
    curl -X POST http://127.0.0.1:8000/users/ \
      -H "Content-Type: application/json" \
      -d '{"username":"张三","email":"zhang@example.com","password":"12345678"}'

    curl -X POST http://127.0.0.1:8000/users/ \
      -H "Content-Type: application/json" \
      -d '{"username":"李四","email":"li@example.com","password":"12345678"}'

    curl http://127.0.0.1:8000/users/

    curl http://127.0.0.1:8000/users/1

    curl -X PATCH http://127.0.0.1:8000/users/1 \
      -H "Content-Type: application/json" \
      -d '{"username":"张三丰"}'

    curl -X DELETE http://127.0.0.1:8000/users/1

    # ─── 文章 ───
    curl -X POST "http://127.0.0.1:8000/posts/?user_id=1" \
      -H "Content-Type: application/json" \
      -d '{"title":"Hello FastAPI","content":"这是第一篇文章"}'

    curl -X POST "http://127.0.0.1:8000/posts/?user_id=1" \
      -H "Content-Type: application/json" \
      -d '{"title":"SQLAlchemy 笔记","content":"ORM 让数据库操作更优雅"}'

    # 文章列表（含作者，一次 JOIN 解决 N+1）
    curl http://127.0.0.1:8000/posts/

    curl http://127.0.0.1:8000/posts/1

    curl -X PATCH http://127.0.0.1:8000/posts/1 \
      -H "Content-Type: application/json" \
      -d '{"published":true}'

    curl -X DELETE http://127.0.0.1:8000/posts/1
"""

from fastapi import FastAPI
from database import engine, Base
from routers import users, posts

# 建表（开发环境；生产用 Alembic）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog API",
    description="FastAPI + SQLAlchemy 博客系统 — 标准项目结构演示",
    version="1.0.0",
)

# 注册路由
app.include_router(users.router)
app.include_router(posts.router)


@app.get("/")
def root():
    return {
        "message": "Blog API",
        "docs": "/docs",
        "endpoints": {
            "POST /users/": "创建用户",
            "GET /users/": "用户列表",
            "GET /users/{id}": "用户详情",
            "PATCH /users/{id}": "更新用户",
            "DELETE /users/{id}": "删除用户",
            "POST /posts/?user_id=1": "创建文章",
            "GET /posts/": "文章列表（含作者，已解决 N+1）",
            "GET /posts/{id}": "文章详情",
            "PATCH /posts/{id}": "更新文章",
            "DELETE /posts/{id}": "删除文章",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
