"""
app/routers/posts.py — 文章路由 + 外部服务模拟

包含：
  1. 文章 CRUD：POST /posts, GET /posts, GET /posts/{id}, PATCH /posts/{id}, DELETE /posts/{id}
  2. 外部服务模拟：GET /weather（用于 Mock 测试）
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Post
from app.schemas import PostCreate, PostUpdate, PostResponse
from app.auth import get_current_user, require_editor

# ── 创建路由器 ──
router = APIRouter(tags=["文章与外部服务"])


# ═══════════════════════════════════════════════════════════
# 辅助函数：组装 PostResponse
# ═══════════════════════════════════════════════════════════

def _post_to_response(post: Post) -> PostResponse:
    """将 ORM 对象转为 Pydantic 响应（附带作者名）"""
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        user_id=post.user_id,
        author_username=post.author.username if post.author else "",
        created_at=post.created_at,
    )


# ═══════════════════════════════════════════════════════════
# 1. 文章 CRUD
# ═══════════════════════════════════════════════════════════

@router.post("/posts", response_model=PostResponse, status_code=201)
def create_post(
    data: PostCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """
    创建文章 —— 需要 editor 或 admin 角色。

    测试要点：
      - editor/admin → 201
      - 普通 user → 403
    """
    post = Post(
        title=data.title,
        content=data.content,
        user_id=current_user.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_to_response(post)


@router.get("/posts", response_model=list[PostResponse])
def list_posts(db: Session = Depends(get_db)):
    """获取所有文章（公开接口）"""
    posts = db.query(Post).all()
    return [_post_to_response(p) for p in posts]


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """
    获取单篇文章。

    测试要点：
      - 存在的 ID → 200
      - 不存在的 ID → 404
    """
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return _post_to_response(post)


@router.patch("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新文章 —— 只有作者本人或管理员可以修改。

    测试要点：
      - 作者本人 → 200
      - admin → 200
      - 非作者普通用户 → 403
    """
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 所有权检查：仅作者或管理员
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能修改自己的文章")

    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content

    db.commit()
    db.refresh(post)
    return _post_to_response(post)


@router.delete("/posts/{post_id}", status_code=200)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除文章 —— 只有作者本人或管理员可以删除。

    测试要点：
      - 作者本人 → 200
      - admin → 200
      - 非作者 → 403
      - 删除后 GET → 404
    """
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能删除自己的文章")

    db.delete(post)
    db.commit()
    return {"message": f"文章 '{post.title}' 已删除"}


# ═══════════════════════════════════════════════════════════
# 2. 外部服务模拟端点（用于 Mock 测试）
# ═══════════════════════════════════════════════════════════

async def fetch_weather_from_external(city: str) -> dict:
    """
    模拟调用外部天气 API（测试时会被 Mock）。
    实际项目用 httpx 调第三方；这里直接返回假数据。
    """
    return {
        "city": city,
        "temperature": 22,
        "condition": "晴",
        "source": "external-api",
    }


@router.get("/weather")
async def get_weather(city: str = "北京"):
    """
    获取天气 —— 模拟调用外部 API。

    测试要点：
      - 正常返回 → 200
      - Mock 外部 API 超时 → 应返回 500 或降级数据
    """
    try:
        result = await fetch_weather_from_external(city)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="天气服务暂不可用")
