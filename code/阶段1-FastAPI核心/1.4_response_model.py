"""
1.4 响应模型与状态码

运行方式：
    uvicorn 1.4_response_model:app --reload

核心知识点：
    - response_model 过滤敏感字段（密码绝不返回）
    - response_model_include / exclude 灵活过滤
    - status_code 正确设置 HTTP 状态码
    - 输入模型和输出模型分离设计
"""

from fastapi import FastAPI, status
from pydantic import BaseModel, Field
from typing import List

app = FastAPI(title="用户管理 API — 响应模型演示")


# ===== 输入模型（创建时接收） =====
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: str
    password: str = Field(min_length=8, description="明文密码，仅输入用")


# ===== 公开输出模型（绝不包含密码！） =====
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool


# ===== 详情输出模型（公开 + 额外字段） =====
class UserDetailResponse(UserResponse):
    """继承公开模型，增加登录时间"""
    last_login: str | None = None


# ===== 模拟数据库（包含所有字段） =====
users_db: dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "password_hash": "$2b$12$abc123...",
        "is_active": True,
        "last_login": "2024-01-15T10:30:00",
        "internal_notes": "VIP 用户",  # 内部备注，绝不暴露
    },
    2: {
        "id": 2,
        "name": "Bob",
        "email": "bob@example.com",
        "password_hash": "$2b$12$def456...",
        "is_active": False,
        "last_login": None,
        "internal_notes": "",
    },
}
next_id = 3


# ===== 创建用户（response_model 过滤密码） =====
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def create_user(user: UserCreate):
    """创建用户：接收 UserCreate（含密码），返回 UserResponse（无密码）"""
    global next_id
    # 模拟：密码哈希
    new_user = {
        "id": next_id,
        "name": user.name,
        "email": user.email,
        "password_hash": f"hashed({user.password})",
        "is_active": True,
        "last_login": None,
        "internal_notes": "",
    }
    users_db[next_id] = new_user
    next_id += 1
    return new_user  # response_model 自动过滤掉 password_hash 和 internal_notes


# ===== 列表（返回 List[response_model]） =====
@app.get("/users", response_model=List[UserResponse], tags=["Users"])
async def list_users():
    """获取用户列表 — 每个用户都被 UserResponse 过滤"""
    return list(users_db.values())


# ===== 详情（用 include 过滤） =====
@app.get("/users/{user_id}", response_model=UserDetailResponse, tags=["Users"])
async def get_user(user_id: int):
    """获取用户详情：比列表多了 last_login 字段"""
    if user_id not in users_db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="用户不存在")
    return users_db[user_id]


# ===== 最小视图（用 exclude 只保留 name+email） =====
@app.get("/users/{user_id}/minimal", response_model=UserResponse,
         response_model_include={"name", "email"}, tags=["Users"])
async def get_user_minimal(user_id: int):
    """只返回 name 和 email — response_model_include 的用法"""
    if user_id not in users_db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="用户不存在")
    return users_db[user_id]


# ===== 删除（204 No Content） =====
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
async def delete_user(user_id: int):
    """删除成功返回 204 — 没有响应体"""
    if user_id not in users_db:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="用户不存在")
    del users_db[user_id]
    # 204 不返回任何内容
    return None


# ===== 启动 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
