"""
2.1 请求数据的高级验证 — 可运行 Demo

启动方式:
    cd 阶段2-请求与响应/code/2.1-高级验证
    uvicorn main:app --reload

然后访问:
    http://127.0.0.1:8000/docs    — 在 Swagger 中交互式测试
    http://127.0.0.1:8000/redoc   — ReDoc 文档

测试命令（用 curl 或浏览器）:
    # 测试 Query() 校验
    curl "http://127.0.0.1:8000/items/?page=1&q=phone&category=electronics&tags=a&tags=b"
    curl "http://127.0.0.1:8000/items/?q=ab"              # q 太短，应返回 422
    curl "http://127.0.0.1:8000/items/?q=SELECT * FROM"   # 含特殊字符，应返回 422
    curl "http://127.0.0.1:8000/items/"                   # 缺少 category，应返回 422

    # 测试 Path() 校验
    curl "http://127.0.0.1:8000/items/42"
    curl "http://127.0.0.1:8000/items/0"                  # item_id <= 0，应返回 422
    curl "http://127.0.0.1:8000/items/abc"                # item_id 不是 int，应返回 422

    # 测试 Field() + 验证器（JSON 请求体）
    curl -X POST "http://127.0.0.1:8000/users/" \
         -H "Content-Type: application/json" \
         -d '{"username":"john_doe","email":"john@example.com","age":25,"phone":"13800138000"}'

    curl -X POST "http://127.0.0.1:8000/users/" \
         -H "Content-Type: application/json" \
         -d '{"username":"admin","email":"bad-email","age":200,"phone":"12345"}'
         # 应返回多个 422 错误：admin 是保留用户名、邮箱格式错误、年龄超限、手机号格式错误

    # 测试订单（model_validator 跨字段校验）
    curl -X POST "http://127.0.0.1:8000/orders/" \
         -H "Content-Type: application/json" \
         -d '{"product_id":1,"quantity":5000,"unit_price":50}'
         # 总额 250000 > 100000，应返回 422
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import FastAPI, Query, Path, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="2.1 高级验证 Demo",
    description="演示 Query()、Path()、Field()、@field_validator、@model_validator",
    version="1.0.0",
)


# ═══════════════════════════════════════════════════════════
# 枚举定义
# ═══════════════════════════════════════════════════════════
class ProductCategory(str, Enum):
    electronics = "electronics"
    clothing = "clothing"
    food = "food"


# ═══════════════════════════════════════════════════════════
# Pydantic 模型 — 演示 Field() 和自定义验证器
# ═══════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    """用户注册模型 — 完整的字段校验示例"""
    username: str = Field(
        default=...,
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="用户名，3-30 个字符，仅支持字母、数字、下划线",
        examples=["john_doe"],
    )

    email: str = Field(
        default=...,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        description="有效邮箱地址",
        examples=["user@example.com"],
    )

    age: int = Field(
        default=...,
        gt=0,
        lt=150,
        description="年龄（1-149）",
        examples=[25],
    )

    phone: str = Field(
        default=...,
        min_length=11,
        max_length=11,
        pattern=r"^1[3-9]\d{9}$",
        description="中国大陆 11 位手机号码",
        examples=["13800138000"],
    )

    bio: str | None = Field(
        default=None,
        max_length=500,
        description="个人简介（可选）",
    )

    # ── 单字段验证器 ──
    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, v: str) -> str:
        """用户名不能是保留字"""
        reserved = {"admin", "root", "system", "api", "null", "test"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' 是保留用户名，请换一个")
        return v

    @field_validator("username")
    @classmethod
    def username_no_special_chars(cls, v: str) -> str:
        """用户名不能有特殊字符（双重保险——Field 的 pattern 已做过基础校验）"""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字、下划线")
        return v

    @field_validator("phone")
    @classmethod
    def phone_valid_chinese(cls, v: str) -> str:
        """校验中国大陆手机号号段"""
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("请输入有效的中国大陆手机号码（11 位，1 开头）")
        return v


class OrderCreate(BaseModel):
    """订单模型 — 演示跨字段校验"""
    product_id: int = Field(gt=0, description="商品 ID")
    quantity: int = Field(gt=0, le=9999, description="购买数量")
    unit_price: float = Field(gt=0, le=999999.99, description="单价（元）")
    discount_code: str | None = Field(default=None, min_length=4, max_length=10)

    @model_validator(mode="after")
    def total_must_be_reasonable(self) -> "OrderCreate":
        """订单总额不能超过 10 万元"""
        total = self.quantity * self.unit_price
        if total > 100_000:
            raise ValueError(
                f"订单总额 ¥{total:,.2f} 超过上限 ¥100,000.00。"
                f"请减少数量或选择其他商品。"
            )
        return self

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        """前置处理：如果 discount_code 存在，自动转为大写"""
        if isinstance(data, dict) and "discount_code" in data and data["discount_code"]:
            data["discount_code"] = data["discount_code"].strip().upper()
        return data


# ═══════════════════════════════════════════════════════════
# 路由 1 — 演示 Query() 查询参数校验
# ═══════════════════════════════════════════════════════════

@app.get("/items/", tags=["1. Query() 校验"])
async def list_items(
    page: int = Query(default=1, ge=1, description="页码（从 1 开始）"),
    q: str | None = Query(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9一-鿿\s]+$",  # 中英文+数字+空格
        alias="search",
        description="搜索关键词（3-50 字符，仅中英文和数字）",
    ),
    category: ProductCategory = Query(
        default=...,
        description="商品分类（必选）",
    ),
    tags: list[str] = Query(
        default=[],
        description="标签筛选（可多次传值：?tags=a&tags=b）",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        alias="page-size",
        description="每页条数（1-100）",
    ),
):
    """列表查询 — 展示 Query() 的各种校验参数"""
    return {
        "message": "查询成功",
        "params": {
            "page": page,
            "q": q,
            "category": category,
            "tags": tags,
            "page_size": page_size,
        }
    }


# ═══════════════════════════════════════════════════════════
# 路由 2 — 演示 Path() 路径参数校验
# ═══════════════════════════════════════════════════════════

@app.get("/items/{item_id}", tags=["2. Path() 校验"])
async def get_item(
    item_id: int = Path(
        gt=0,
        le=999999,
        title="商品 ID",
        description="数据库中商品的唯一标识（1-999999）",
        examples=[42, 100],
    ),
):
    """获取单个商品 — 展示 Path() 的数值范围校验"""
    return {
        "message": "获取成功",
        "item_id": item_id,
        "item": {"name": f"示例商品 #{item_id}", "price": 99.99},
    }


@app.get("/products/{category}", tags=["2. Path() 校验"])
async def get_products_by_category(
    category: ProductCategory = Path(
        description="商品分类（枚举约束）",
    ),
):
    """按分类获取商品 — 展示 Path() 的枚举约束"""
    mock_products = {
        "electronics": ["手机", "电脑", "耳机"],
        "clothing": ["T恤", "牛仔裤", "运动鞋"],
        "food": ["面包", "牛奶", "水果"],
    }
    return {"category": category, "products": mock_products.get(category, [])}


# ═══════════════════════════════════════════════════════════
# 路由 3 — 演示 Field() + 验证器（Pydantic 模型校验）
# ═══════════════════════════════════════════════════════════

@app.post("/users/", tags=["3. Field() + 验证器"], status_code=201)
async def create_user(user: UserCreate):
    """创建用户 — 展示 Pydantic Field() + @field_validator"""
    return {
        "message": "用户创建成功",
        "user": {
            "username": user.username,
            "email": user.email,
            "age": user.age,
            "phone": user.phone,
            "registered_at": datetime.now().isoformat(),
        },
    }


# ═══════════════════════════════════════════════════════════
# 路由 4 — 演示 @model_validator 跨字段校验
# ═══════════════════════════════════════════════════════════

@app.post("/orders/", tags=["4. model_validator"], status_code=201)
async def create_order(order: OrderCreate):
    """创建订单 — 展示 @model_validator 跨字段校验"""
    total = order.quantity * order.unit_price
    return {
        "message": "订单创建成功",
        "order": {
            "product_id": order.product_id,
            "quantity": order.quantity,
            "unit_price": order.unit_price,
            "total": round(total, 2),
            "discount_code": order.discount_code,
        },
        "created_at": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# 路由 5 — 查看 422 错误格式（方便学习错误结构）
# ═══════════════════════════════════════════════════════════

@app.get("/demo/validation-error", tags=["5. 验证失败示例"])
async def demo_validation_error(
    username: str = Query(
        min_length=5,
        max_length=10,
        pattern=r"^[A-Z]+$",
        description="尝试传入不符合规则的参数查看 422 错误格式",
    ),
):
    """访问 /demo/validation-error?username=ab 即可看到 422 错误格式"""
    return {"username": username}


# ═══════════════════════════════════════════════════════════
# 全局异常处理器 — 统一错误格式
# ═══════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc: HTTPException):
    """统一 HTTP 异常的错误格式"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": f"HTTP_{exc.status_code}",
            "detail": exc.detail,
            "path": request.url.path,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
