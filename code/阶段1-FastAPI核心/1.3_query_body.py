"""
1.3 查询参数与请求体

运行方式：
    uvicorn 1.3_query_body:app --reload

接口：
    GET  /products          搜索 + 筛选 + 分页
    POST /products          创建商品（Pydantic 请求体）
    GET  /products/{id}     获取单个商品

在 /docs 页面可以看到请求体的完整 Schema。
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import Annotated, Optional

app = FastAPI(title="商品管理 API")


# ===== Pydantic 模型 =====
class ProductCreate(BaseModel):
    """创建商品时的请求体"""
    name: str = Field(
        min_length=1,
        max_length=100,
        description="商品名称",
        examples=["机械键盘"],
    )
    category: str = Field(
        min_length=1,
        max_length=50,
        description="商品分类",
    )
    price: float = Field(
        gt=0,
        description="价格（必须大于 0）",
        examples=[399.0],
    )
    in_stock: bool = Field(
        default=True,
        description="是否有库存",
    )


# ===== 模拟数据库 =====
products_db: list[dict] = [
    {"id": 1, "name": "机械键盘", "category": "electronics", "price": 399.0, "in_stock": True},
    {"id": 2, "name": "Python 编程书", "category": "books", "price": 79.0, "in_stock": True},
    {"id": 3, "name": "T恤", "category": "clothing", "price": 129.0, "in_stock": False},
    {"id": 4, "name": "无线耳机", "category": "electronics", "price": 299.0, "in_stock": True},
    {"id": 5, "name": "算法导论", "category": "books", "price": 108.0, "in_stock": True},
]


# ===== 搜索 + 筛选 + 分页（Annotated 写法） =====
@app.get("/products", tags=["Products"])
async def search_products(
    # 搜索关键词
    q: Annotated[Optional[str], Query(description="搜索商品名称")] = None,
    # 分类筛选
    category: Annotated[Optional[str], Query(description="分类筛选")] = None,
    # 价格区间
    min_price: Annotated[Optional[float], Query(ge=0, description="最低价")] = None,
    max_price: Annotated[Optional[float], Query(ge=0, description="最高价")] = None,
    # 分页
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    size: Annotated[int, Query(ge=1, le=50, description="每页数量")] = 10,
):
    """搜索商品：支持关键词、分类、价格区间筛选 + 分页"""
    results = products_db.copy()

    # 关键词搜索
    if q:
        results = [p for p in results if q.lower() in p["name"].lower()]

    # 分类筛选
    if category:
        results = [p for p in results if p["category"] == category]

    # 价格区间
    if min_price is not None:
        results = [p for p in results if p["price"] >= min_price]
    if max_price is not None:
        results = [p for p in results if p["price"] <= max_price]

    # 分页
    total = len(results)
    start = (page - 1) * size
    end = start + size

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": results[start:end],
    }


# ===== 创建商品（Pydantic 请求体） =====
@app.post("/products", status_code=201, tags=["Products"])
async def create_product(product: ProductCreate):
    """创建商品 — 请求体由 Pydantic 自动校验"""
    new_id = max(p["id"] for p in products_db) + 1
    new_product = {"id": new_id, **product.model_dump()}
    products_db.append(new_product)
    return new_product


# ===== 获取单个商品 =====
@app.get("/products/{product_id}", tags=["Products"])
async def get_product(product_id: int):
    """获取单个商品，演示路径参数 + 查询参数混用"""
    for p in products_db:
        if p["id"] == product_id:
            return p
    # FastAPI 自动返回 200，但数据为 null
    # 下一章（1.5）会学会正确的 404 处理
    return None


# ===== 启动 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
