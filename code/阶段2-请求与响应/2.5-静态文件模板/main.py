"""
2.5 静态文件与模板 — 可运行 Demo

这是一个简易的图书管理后台，演示：
- StaticFiles 挂载静态资源（CSS）
- Jinja2 模板渲染（列表、表单）
- 模板继承（base.html → 子页面）
- 完整的 CRUD 操作（表单提交 → 重定向）

启动方式:
    cd 阶段2-请求与响应/code/2.5-静态文件模板
    pip install jinja2 aiofiles    # 首次运行需要安装
    uvicorn main:app --reload

然后在浏览器中访问:
    http://127.0.0.1:8000/admin        — 图书管理后台（列表页）
    http://127.0.0.1:8000/             — 首页
    http://127.0.0.1:8000/docs         — API 文档
"""

from datetime import datetime

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="2.5 静态文件与模板 Demo",
    description="图书管理后台 — 演示 StaticFiles + Jinja2 模板 + CRUD",
    version="1.0.0",
)

# ── 挂载静态文件 — 把 /static URL 映射到 ./static 目录 ──
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── 配置 Jinja2 模板引擎 ──
templates = Jinja2Templates(directory="templates")

# ═══════════════════════════════════════════════════════════
# 模拟数据库
# ═══════════════════════════════════════════════════════════
books_db: dict[int, dict] = {
    1: {
        "id": 1,
        "title": "Python FastAPI 入门",
        "author": "小明",
        "price": 59.9,
        "category": "科技",
        "created_at": "2024-01-15",
    },
    2: {
        "id": 2,
        "title": "百年孤独",
        "author": "马尔克斯",
        "price": 39.5,
        "category": "文学",
        "created_at": "2024-02-20",
    },
    3: {
        "id": 3,
        "title": "人类简史",
        "author": "赫拉利",
        "price": 49.0,
        "category": "历史",
        "created_at": "2024-03-10",
    },
    4: {
        "id": 4,
        "title": "存在与虚无",
        "author": "萨特",
        "price": 79.0,
        "category": "哲学",
        "created_at": "2024-04-05",
    },
}
_next_id = 5

CATEGORIES = ["文学", "科技", "历史", "哲学"]

# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════
def get_stats() -> dict:
    """计算图书统计数据"""
    total = len(books_db)
    total_value = sum(b["price"] for b in books_db.values())
    by_category: dict[str, int] = {}
    for book in books_db.values():
        cat = book["category"]
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "total_books": total,
        "total_value": round(total_value, 2),
        "by_category": by_category,
    }

# ═══════════════════════════════════════════════════════════
# 首页
# ═══════════════════════════════════════════════════════════

@app.get("/")
async def home(request: Request):
    """首页——渲染 Jinja2 模板"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "图书管理系统",
        "stats": get_stats(),
        "recent_books": sorted(
            books_db.values(), key=lambda b: b["created_at"], reverse=True
        )[:3],
    })

# ═══════════════════════════════════════════════════════════
# 管理后台 — 列表页
# ═══════════════════════════════════════════════════════════

@app.get("/admin")
async def admin_books_list(request: Request):
    """图书列表页"""
    return templates.TemplateResponse("admin/books.html", {
        "request": request,
        "title": "图书管理后台",
        "books": sorted(books_db.values(), key=lambda b: b["id"]),
        "stats": get_stats(),
    })

# ═══════════════════════════════════════════════════════════
# 管理后台 — 新建图书表单
# ═══════════════════════════════════════════════════════════

@app.get("/admin/books/new")
async def admin_new_book_form(request: Request):
    """新建图书表单页"""
    return templates.TemplateResponse("admin/book_form.html", {
        "request": request,
        "title": "新建图书",
        "book": None,  # None 表示新建模式
        "categories": CATEGORIES,
    })

# ═══════════════════════════════════════════════════════════
# 管理后台 — 编辑图书表单
# ═══════════════════════════════════════════════════════════

@app.get("/admin/books/{book_id}/edit")
async def admin_edit_book_form(request: Request, book_id: int):
    """编辑图书表单页"""
    book = books_db.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    return templates.TemplateResponse("admin/book_form.html", {
        "request": request,
        "title": f"编辑: {book['title']}",
        "book": book,
        "categories": CATEGORIES,
    })

# ═══════════════════════════════════════════════════════════
# API — 创建图书（表单提交）
# ═══════════════════════════════════════════════════════════

@app.post("/admin/books")
async def admin_create_book(
    title: str = Form(..., min_length=1, max_length=200),
    author: str = Form(..., min_length=1, max_length=100),
    price: float = Form(..., gt=0, le=99999.99),
    category: str = Form(..., min_length=1),
):
    """创建图书——处理表单提交，然后重定向回列表页"""
    global _next_id
    now = datetime.now().strftime("%Y-%m-%d")
    books_db[_next_id] = {
        "id": _next_id,
        "title": title.strip(),
        "author": author.strip(),
        "price": price,
        "category": category,
        "created_at": now,
    }
    _next_id += 1
    # PRG 模式：POST 后重定向到 GET，避免刷新页面时重复提交
    return RedirectResponse(url="/admin", status_code=303)

# ═══════════════════════════════════════════════════════════
# API — 更新图书（表单提交）
# ═══════════════════════════════════════════════════════════

@app.post("/admin/books/{book_id}/update")
async def admin_update_book(
    book_id: int,
    title: str = Form(..., min_length=1, max_length=200),
    author: str = Form(..., min_length=1, max_length=100),
    price: float = Form(..., gt=0, le=99999.99),
    category: str = Form(..., min_length=1),
):
    """更新图书——处理表单提交，然后重定向回列表页"""
    book = books_db.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    book.update({
        "title": title.strip(),
        "author": author.strip(),
        "price": price,
        "category": category,
    })
    return RedirectResponse(url="/admin", status_code=303)

# ═══════════════════════════════════════════════════════════
# API — 删除图书
# ═══════════════════════════════════════════════════════════

@app.get("/admin/books/{book_id}/delete")
async def admin_delete_book(book_id: int):
    """删除图书——通过 GET 链接触发，然后重定向"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="图书不存在")
    del books_db[book_id]
    return RedirectResponse(url="/admin", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
