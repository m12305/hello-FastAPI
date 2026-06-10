"""
1.5 错误处理

运行方式：
    uvicorn 1.5_error_handling:app --reload

接口：
    GET    /users/{id}     查找用户
    POST   /users          创建用户
    DELETE /users/{id}     删除用户
    POST   /orders         创建订单

知识点：
    - HTTPException 主动抛出错误
    - 不同场景用不同状态码
    - 自定义异常类 + 异常处理器
    - 统一错误响应格式
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

app = FastAPI(title="错误处理演示 API")


# ===== 数据 =====
users_db = {
    1: {"id": 1, "username": "alice", "email": "alice@example.com", "is_active": True},
    2: {"id": 2, "username": "bob", "email": "bob@example.com", "is_active": False},
}

products_db = {
    1: {"id": 1, "name": "机械键盘", "stock": 10},
    2: {"id": 2, "name": "鼠标", "stock": 0},
}

next_user_id = 3


# ===== 模型 =====
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str
    age: int = Field(ge=18, le=120)


class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


# ===== 自定义异常类 =====
class InsufficientStockError(Exception):
    """库存不足异常"""
    def __init__(self, product_id: int, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available


# ===== 全局异常处理器 =====

@app.exception_handler(InsufficientStockError)
async def stock_error_handler(request: Request, exc: InsufficientStockError):
    """处理库存不足异常"""
    return JSONResponse(
        status_code=409,
        content={
            "error": "INSUFFICIENT_STOCK",
            "message": f"商品 {exc.product_id} 库存不足",
            "requested": exc.requested,
            "available": exc.available,
        },
    )


@app.exception_handler(HTTPException)
async def http_handler(request: Request, exc: HTTPException):
    """统一 HTTPException 的响应格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.status_code,
            "message": str(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """自定义参数校验错误的格式"""
    details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        details.append({"field": field, "message": error["msg"]})

    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "details": details,
        },
    )


# ===== 兜底异常 =====
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试",
        },
    )


# ===== 路由 =====

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: int):
    """获取用户 — 404 示例"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return users_db[user_id]


@app.post("/users", status_code=201, tags=["Users"])
async def create_user(user: UserCreate):
    """创建用户 — 409 冲突示例 + Pydantic 自动校验"""
    global next_user_id
    # 检查用户名重复
    for u in users_db.values():
        if u["username"] == user.username:
            raise HTTPException(
                status_code=409,
                detail=f"用户名 '{user.username}' 已被占用",
            )
    new_user = {"id": next_user_id, **user.model_dump(), "is_active": True}
    users_db[next_user_id] = new_user
    next_user_id += 1
    return new_user


@app.delete("/users/{user_id}", tags=["Users"])
async def delete_user(user_id: int):
    """删除用户 — 403 禁止删除示例"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    if user_id == 1:
        raise HTTPException(status_code=403, detail="不能删除超级管理员")
    del users_db[user_id]
    return {"message": f"用户 {user_id} 已删除"}


@app.post("/orders", status_code=201, tags=["Orders"])
async def create_order(order: OrderCreate):
    """创建订单 — 自定义异常示例"""
    # 商品存在性检查
    if order.product_id not in products_db:
        raise HTTPException(
            status_code=404,
            detail=f"商品 {order.product_id} 不存在",
        )

    product = products_db[order.product_id]

    # 库存检查 — 使用自定义异常
    if product["stock"] < order.quantity:
        raise InsufficientStockError(
            product_id=order.product_id,
            requested=order.quantity,
            available=product["stock"],
        )

    # 扣减库存
    product["stock"] -= order.quantity
    return {
        "message": "订单创建成功",
        "product": product["name"],
        "quantity": order.quantity,
        "remaining_stock": product["stock"],
    }


# ===== 启动 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
