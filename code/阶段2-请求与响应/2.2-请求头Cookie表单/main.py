"""
2.2 请求头、Cookie 与表单 — 可运行 Demo

启动方式:
    cd 阶段2-请求与响应/code/2.2-请求头Cookie表单
    uvicorn main:app --reload

然后访问 http://127.0.0.1:8000/docs 交互式测试。

测试命令:
    # ─── Header() ───
    curl -H "X-API-Key: my-secret-key" http://127.0.0.1:8000/whoami
    curl -H "X-API-Key: my-secret-key" -H "X-Request-ID: test-123" http://127.0.0.1:8000/whoami

    # ─── Cookie() — 读取 ───
    curl -H "Cookie: session_id=abc123; csrf-token=xyz789" http://127.0.0.1:8000/read-cookies

    # ─── Cookie() — 设置 ───
    curl -c - -X POST http://127.0.0.1:8000/login
    curl -c - -X POST http://127.0.0.1:8000/logout

    # ─── Form() ───
    curl -X POST http://127.0.0.1:8000/form/login \
         -d "username=john_doe&password=secret123"

    # ─── 文件上传 ───
    curl -X POST http://127.0.0.1:8000/upload/image \
         -F "file=@你的图片路径.jpg"
         # Windows PowerShell 示例:
         # Invoke-RestMethod -Uri http://127.0.0.1:8000/upload/image -Method Post -Form @{file=Get-Item .\test.png}

    # ─── 多文件上传 ───
    curl -X POST http://127.0.0.1:8000/upload/multiple \
         -F "files=@图片1.jpg" -F "files=@图片2.png"

    # ─── 表单 + 文件混合 ───
    curl -X POST http://127.0.0.1:8000/products/with-image \
         -F "name=测试商品" -F "price=99.9" -F "category=电子产品" \
         -F "image=@图片.jpg"
"""

import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import (
    FastAPI, Header, Cookie, Form, File, UploadFile, Response, HTTPException
)
from fastapi.responses import JSONResponse

# ═══════════════════════════════════════════════════════════
# 应用初始化
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="2.2 请求头、Cookie、表单、文件上传 Demo",
    description="演示 Header()、Cookie()、Form()、File()、UploadFile 的用法",
    version="1.0.0",
)

# 上传目录
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 模拟的文件元数据库
files_db: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════
def detect_real_type(content: bytes) -> str | None:
    """通过文件头魔数检测真实文件类型"""
    if content[:4] == b'\x89PNG':      return 'image/png'
    if content[:3] == b'\xff\xd8\xff': return 'image/jpeg'
    if content[:3] == b'GIF8':         return 'image/gif'
    if content[:4] == b'RIFF':         return 'image/webp'
    return None


# ═══════════════════════════════════════════════════════════
# 1. Header() — 读取请求头
# ═══════════════════════════════════════════════════════════

@app.get("/whoami", tags=["1. Header()"])
async def whoami(
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    x_api_key: str = Header(default=..., alias="X-API-Key", description="API 密钥（必选）"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    accept_language: str | None = Header(default=None),
):
    """获取请求的元信息——演示 Header() 的各种用法"""
    return {
        "client_info": {
            "user_agent": user_agent,
            "accept_language": accept_language,
        },
        "auth": {
            "api_key_provided": bool(x_api_key),
            "api_key_masked": x_api_key[:4] + "****" if x_api_key else None,
        },
        "tracing": {
            "request_id": x_request_id or "not provided",
        },
    }


# ═══════════════════════════════════════════════════════════
# 2. Cookie() — 读取和设置 Cookie
# ═══════════════════════════════════════════════════════════

@app.get("/read-cookies", tags=["2. Cookie()"])
async def read_cookies(
    session_id: str | None = Cookie(default=None),
    csrf_token: str | None = Cookie(default=None, alias="csrf-token"),
):
    """读取客户端发来的 Cookie"""
    return {
        "cookies_found": {
            "session_id": session_id,
            "csrf_token": csrf_token,
        }
    }


@app.post("/login", tags=["2. Cookie()"])
async def login(response: Response):
    """模拟登录——服务器设置 Cookie"""
    session_token = uuid.uuid4().hex[:16]
    response.set_cookie(
        key="session_id",
        value=session_token,
        max_age=3600,           # 1 小时后过期
        httponly=True,          # JavaScript 无法读取（防 XSS）
        secure=False,           # 开发环境允许 HTTP。生产环境应设为 True
        samesite="lax",         # 防止 CSRF 攻击
    )
    return {
        "message": "登录成功",
        "session_token": session_token,
        "note": "Cookie 已设置，查看响应头中的 Set-Cookie",
    }


@app.post("/logout", tags=["2. Cookie()"])
async def logout(response: Response):
    """模拟登出——删除 Cookie"""
    response.delete_cookie(key="session_id")
    return {"message": "已登出，Cookie 已清除"}


# ═══════════════════════════════════════════════════════════
# 3. Form() — 处理表单提交
# ═══════════════════════════════════════════════════════════

@app.post("/form/login", tags=["3. Form()"])
async def form_login(
    username: str = Form(default=..., min_length=3, max_length=30),
    password: str = Form(default=..., min_length=6),
    remember_me: bool = Form(default=False),
):
    """模拟表单登录——演示 Form() 参数校验"""
    return {
        "message": "表单登录处理成功",
        "username": username,
        "remember_me": remember_me,
        "password_length": len(password),  # 密码已接收但不应在响应中明文返回
    }


# ═══════════════════════════════════════════════════════════
# 4. File() / UploadFile — 文件上传
# ═══════════════════════════════════════════════════════════

@app.post("/upload/single", tags=["4. 文件上传"])
async def upload_single_file(
    file: UploadFile = File(default=..., description="要上传的文件"),
):
    """单文件上传——返回文件基本信息"""
    content = await file.read()
    return {
        "message": "文件接收成功",
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "size_readable": f"{len(content) / 1024:.1f} KB",
    }


@app.post("/upload/image", tags=["4. 文件上传"])
async def upload_image(file: UploadFile = File(..., description="图片文件")):
    """图片上传——含类型和大小校验"""
    # 1. 允许的图片类型
    ALLOWED_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 '{file.content_type}'。"
                   f"仅支持：{', '.join(ALLOWED_TYPES.keys())}",
        )

    # 2. 读取并校验大小
    content = await file.read()
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB

    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小 {len(content) / 1024 / 1024:.1f}MB "
                   f"超过上限 {MAX_SIZE / 1024 / 1024:.0f}MB",
        )

    # 3. 魔数检测——防止伪造 Content-Type
    real_type = detect_real_type(content)
    if real_type and real_type != file.content_type:
        raise HTTPException(
            status_code=400,
            detail=f"文件类型不匹配：声称 {file.content_type}，实际为 {real_type}",
        )

    # 4. 生成安全文件名并保存
    safe_name = f"{uuid.uuid4().hex}{ALLOWED_TYPES[file.content_type]}"
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(content)

    # 5. 记录元数据
    file_id = uuid.uuid4().hex[:8]
    files_db[file_id] = {
        "id": file_id,
        "original_name": file.filename,
        "saved_name": safe_name,
        "size": len(content),
        "content_type": file.content_type,
        "md5": hashlib.md5(content).hexdigest(),
        "uploaded_at": datetime.now().isoformat(),
    }

    return {
        "message": "图片上传成功",
        "file_id": file_id,
        "original_filename": file.filename,
        "size_kb": f"{len(content) / 1024:.1f}",
        "type": file.content_type,
    }


@app.post("/upload/multiple", tags=["4. 文件上传"])
async def upload_multiple_files(
    files: List[UploadFile] = File(default=..., description="多个文件"),
):
    """多文件上传"""
    results = []
    total_size = 0
    MAX_PER_FILE = 3 * 1024 * 1024  # 单文件 3MB 上限

    for file in files:
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_PER_FILE:
            results.append({
                "filename": file.filename,
                "status": "rejected",
                "reason": f"文件 {file_size / 1024 / 1024:.1f}MB 超过单文件 3MB 上限",
            })
            continue

        total_size += file_size
        results.append({
            "filename": file.filename,
            "status": "accepted",
            "size_kb": f"{file_size / 1024:.1f}",
            "content_type": file.content_type,
        })

    return {
        "message": f"批量上传完成：{len([r for r in results if r['status'] == 'accepted'])}/{len(results)} 个文件被接受",
        "total_size_readable": f"{total_size / 1024:.1f} KB" if total_size else "0 KB",
        "files": results,
    }


# ═══════════════════════════════════════════════════════════
# 5. 表单 + 文件混合上传
# ═══════════════════════════════════════════════════════════

@app.post("/products/with-image", tags=["5. 表单+文件混合"])
async def create_product_with_image(
    name: str = Form(..., min_length=1, max_length=100, description="商品名称"),
    price: float = Form(..., gt=0, description="价格（元）"),
    category: str = Form(..., description="分类"),
    image: UploadFile = File(..., description="商品主图"),
    gallery: List[UploadFile] = File(default=[], description="商品图集（可选）"),
):
    """创建商品并上传图片——演示 Form + File 混合"""

    # 处理主图
    image_content = await image.read()
    image_ext = Path(image.filename).suffix if image.filename else ".jpg"
    image_name = f"product_{uuid.uuid4().hex[:8]}{image_ext}"
    (UPLOAD_DIR / image_name).write_bytes(image_content)

    # 处理图集
    gallery_info = []
    for img in gallery:
        img_content = await img.read()
        img_ext = Path(img.filename).suffix if img.filename else ".jpg"
        img_name = f"gallery_{uuid.uuid4().hex[:8]}{img_ext}"
        (UPLOAD_DIR / img_name).write_bytes(img_content)
        gallery_info.append({
            "filename": img.filename,
            "saved_as": img_name,
            "size_kb": f"{len(img_content) / 1024:.1f}",
        })

    return {
        "message": "商品创建成功",
        "product": {
            "name": name,
            "price": price,
            "category": category,
        },
        "image": {
            "filename": image.filename,
            "saved_as": image_name,
            "size_kb": f"{len(image_content) / 1024:.1f}",
        },
        "gallery": gallery_info,
    }


# ═══════════════════════════════════════════════════════════
# 6. 综合演示：文件管理
# ═══════════════════════════════════════════════════════════

@app.post("/files/upload", tags=["6. 综合：文件管理"])
async def files_upload(
    file: UploadFile = File(..., description="要上传的文件"),
    description: str = Form(default="", description="文件描述"),
    tags: str = Form(default="", description="标签（逗号分隔）"),
    x_user_id: str = Header(default="anonymous", alias="X-User-ID"),
    session_id: str | None = Cookie(default=None),
):
    """完整文件上传——综合运用 Header、Cookie、Form、File"""
    content = await file.read()
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB

    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件不能超过 10MB")

    file_id = uuid.uuid4().hex[:12]
    extension = Path(file.filename).suffix if file.filename else ""
    safe_name = f"{file_id}{extension}"
    (UPLOAD_DIR / safe_name).write_bytes(content)

    metadata = {
        "id": file_id,
        "original_name": file.filename,
        "saved_name": safe_name,
        "size": len(content),
        "content_type": file.content_type,
        "md5": hashlib.md5(content).hexdigest(),
        "description": description,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "uploader": x_user_id,
        "session_id": session_id,
        "uploaded_at": datetime.now().isoformat(),
    }
    files_db[file_id] = metadata

    return {
        "message": "上传成功",
        "file_id": file_id,
        "metadata": metadata,
    }


@app.get("/files/", tags=["6. 综合：文件管理"])
async def files_list(
    x_user_id: str = Header(default=..., alias="X-User-ID"),
):
    """列出当前用户的所有文件"""
    user_files = [f for f in files_db.values() if f["uploader"] == x_user_id]
    return {"uploader": x_user_id, "count": len(user_files), "files": user_files}


@app.get("/files/{file_id}", tags=["6. 综合：文件管理"])
async def files_get(file_id: str):
    """获取单个文件元数据"""
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="文件不存在")
    return files_db[file_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
