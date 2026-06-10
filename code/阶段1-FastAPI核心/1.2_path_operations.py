"""
1.2 路径操作（Path Operations）

运行方式：
    uvicorn 1.2_path_operations:app --reload

然后用浏览器或 curl 测试以下接口：
    GET    /todos                获取所有 Todo
    GET    /todos/1              获取单个 Todo
    POST   /todos                创建 Todo
    PUT    /todos/1              完整更新 Todo
    PATCH  /todos/1              部分更新 Todo
    DELETE /todos/1              删除 Todo
    GET    /todos/category/work  按分类筛选
"""

from fastapi import FastAPI, HTTPException, status
from enum import Enum

app = FastAPI(title="TODO API — 路径操作演示")


# ===== 枚举：Todo 分类 =====
class TodoCategory(str, Enum):
    work = "work"
    personal = "personal"
    study = "study"


# ===== 模拟数据库 =====
todos: dict[int, dict] = {
    1: {"id": 1, "title": "学习 FastAPI", "category": "study", "done": False},
    2: {"id": 2, "title": "写周报", "category": "work", "done": True},
    3: {"id": 3, "title": "健身房", "category": "personal", "done": False},
}
next_id: int = 4


# ===== 读取列表 =====
@app.get("/todos", tags=["Todos"])
async def list_todos():
    """获取所有 Todo"""
    return list(todos.values())


# ===== 读取单个（路径参数 + 404） =====
@app.get("/todos/{todo_id}", tags=["Todos"])
async def get_todo(todo_id: int):
    """获取单个 Todo，不存在返回 404"""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} 不存在")
    return todos[todo_id]


# ===== 创建 =====
@app.post("/todos", status_code=status.HTTP_201_CREATED, tags=["Todos"])
async def create_todo(title: str, category: TodoCategory = TodoCategory.personal):
    """创建新 Todo（用查询参数接收数据，仅用于演示）"""
    global next_id
    new_todo = {
        "id": next_id,
        "title": title,
        "category": category.value,
        "done": False,
    }
    todos[next_id] = new_todo
    next_id += 1
    return new_todo


# ===== 完整更新 =====
@app.put("/todos/{todo_id}", tags=["Todos"])
async def replace_todo(todo_id: int, title: str, done: bool):
    """完整替换 Todo"""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} 不存在")
    todos[todo_id] = {"id": todo_id, "title": title, "category": "work", "done": done}
    return todos[todo_id]


# ===== 部分更新 =====
@app.patch("/todos/{todo_id}", tags=["Todos"])
async def update_todo(todo_id: int, title: str | None = None, done: bool | None = None):
    """部分更新 Todo — 只更新传入的字段"""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} 不存在")
    if title is not None:
        todos[todo_id]["title"] = title
    if done is not None:
        todos[todo_id]["done"] = done
    return todos[todo_id]


# ===== 删除 =====
@app.delete("/todos/{todo_id}", tags=["Todos"])
async def delete_todo(todo_id: int):
    """删除 Todo"""
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} 不存在")
    del todos[todo_id]
    return {"message": f"Todo {todo_id} 已删除"}


# ===== 按分类筛选（枚举约束） =====
@app.get("/todos/category/{category}", tags=["Todos"])
async def list_by_category(category: TodoCategory):
    """按分类筛选 Todo（分类用枚举约束）"""
    result = [t for t in todos.values() if t["category"] == category.value]
    return {"category": category.value, "count": len(result), "items": result}


# ===== 启动 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
