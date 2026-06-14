"""
6.4 API 文档与版本化 — 可运行 Demo

运行方式:
    cd code/阶段6-高级特性/6.4-API文档与版本化
    pip install fastapi uvicorn[standard]
    uvicorn main:app --reload
    浏览器打开 http://127.0.0.1:8000/docs

本 Demo 涵盖:
  1. URL 前缀版本化：/api/v1/* 和 /api/v2/*
  2. V1 → V2 的字段演进（phone 新增、role 新增、分页）
  3. openapi_tags 自定义 Swagger 分组
  4. API 废弃标记（deprecated=True + Sunset 头）
  5. 多环境 servers 切换

对比 V1 vs V2:
  V1:
    POST /api/v1/register → 只需 username + email + password
    GET  /api/v1/users     → 无分页，返回 id + username + email
    GET  /api/v1/users/{id}

  V2:
    POST /api/v2/register → 增加了 phone 字段（手机号校验）
    GET  /api/v2/users     → 支持分页，返回 phone + role + created_at
    GET  /api/v2/users/{id}
"""

from fastapi import FastAPI, Response
from app.api.v1.router import router as v1_router
from app.api.v2.router import router as v2_router

# ═══════════════════════════════════════════════════════════
# 应用初始化（丰富的文档定制）
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="🎓 API 版本化 Demo",
    description="""
## 学习 API 文档定制与版本化管理

本 Demo 演示了 FastAPI 中 **URL 前缀版本化** 的标准实践。

### 📦 版本概览
- **V1** (`/api/v1`) — 稳定版，基础字段
- **V2** (`/api/v2`) — 新版本，增加了手机号、角色、分页

### 🔄 演进对比
| 特性 | V1 | V2 |
|------|-----|-----|
| 注册字段 | username, email, password | + phone |
| 用户响应 | id, username, email | + phone, role, created_at |
| 列表分页 | ❌ | ✅ page + size |
| 密码存储 | 明文（演示用）| bcrypt 哈希 |

### 📚 版本化策略
URL 前缀版本化 (`/api/v1/`, `/api/v2/`) 是最推荐的做法：
- ✅ URL 直观，开发者一看就懂
- ✅ Swagger 中可以分组展示
- ✅ 方便在反向代理层做路由
    """,
    version="2.0.0",
    terms_of_service="https://example.com/terms",
    contact={
        "name": "API 支持",
        "email": "api@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    # ── 自定义 Swagger 分组（控制排序和描述）──
    openapi_tags=[
        {"name": "V1-用户", "description": "V1 版用户接口 —— 稳定运行中"},
        {"name": "V2-用户", "description": "V2 版用户接口 —— 最新版本，推荐使用"},
        {"name": "系统", "description": "系统级接口（迁移指南、版本信息）"},
    ],
    # ── 多环境切换 ──
    servers=[
        {"url": "http://127.0.0.1:8000", "description": "本地开发"},
        {"url": "https://staging-api.example.com", "description": "测试环境"},
        {"url": "https://api.example.com", "description": "生产环境"},
    ],
    # ── 自定义文档路径 ──
    docs_url="/docs",
    redoc_url="/redoc",
)

# ═══════════════════════════════════════════════════════════
# 注册多版本路由
# ═══════════════════════════════════════════════════════════

app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")


# ═══════════════════════════════════════════════════════════
# 系统端点（迁移指南 + 模拟旧接口废弃）
# ═══════════════════════════════════════════════════════════

@app.get("/", tags=["系统"], summary="API 版本概览")
def root():
    """API 版本概览和迁移指南"""
    return {
        "service": "API 版本化 Demo",
        "versions": {
            "v1": "稳定运行中（将于 2026-12-31 废弃）",
            "v2": "最新版本（推荐使用）"
        },
        "migration_guide": "GET /migration-guide",
        "docs": "/docs",
    }


@app.get("/migration-guide", tags=["系统"], summary="V1 → V2 迁移指南")
def migration_guide():
    """从 V1 迁移到 V2 的步骤"""
    return {
        "title": "V1 → V2 迁移指南",
        "changes": [
            {
                "field": "phone",
                "type": "新增",
                "说明": "注册时需要提供手机号，格式: 1[3-9]xxxxxxxxx",
            },
            {
                "field": "role",
                "type": "新增",
                "说明": "用户响应中包含 role 字段（user/editor/admin）",
            },
            {
                "field": "created_at",
                "type": "新增",
                "说明": "用户响应中包含注册时间",
            },
            {
                "field": "分页",
                "type": "新增",
                "说明": "GET /users 支持 page + size 参数",
            },
        ],
        "migration_steps": [
            "1. 更新客户端，在注册表单中增加手机号字段",
            "2. 调整用户列表渲染，支持分页（page / size）",
            "3. 更新用户详情页，展示 role 和 created_at",
            "4. 在 2026-12-31 前完成迁移",
        ],
    }


# ── 模拟一个已废弃的旧接口 ──
@app.get(
    "/api/v1/users-legacy",
    tags=["V1-用户"],
    deprecated=True,  # ← Swagger 中标记为废弃
    summary="[已废弃] 旧版用户列表",
    description="此接口将于 2026-12-31 移除，请迁移到 GET /api/v2/users",
)
def legacy_list_users(response: Response):
    """
    已废弃的旧版用户列表。

    响应头中包含了 Deprecation 和 Sunset 信息，
    客户端可以据此自动检测并提示用户升级。
    """
    # ── 添加废弃通知头 ──
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = '</api/v2/users>; rel="successor-version"'

    return {
        "warning": "⚠️ 此接口已废弃，请迁移到 GET /api/v2/users",
        "deprecation_date": "2026-12-31",
        "migration_url": "/api/v2/users",
        "data": [],  # 不再返回真实数据
    }


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  6.4 API 文档与版本化 Demo")
    print("  Swagger: http://127.0.0.1:8000/docs")
    print("  ReDoc:   http://127.0.0.1:8000/redoc")
    print("=" * 60)
    print()
    print("💡 测试提示:")
    print("  1. 打开 /docs 查看 Swagger，观察:")
    print("     - openapi_tags 自定义分组（V1-用户 / V2-用户 / 系统）")
    print("     - servers 多环境下拉切换")
    print("     - 详细的 description 说明")
    print("  2. 对比 V1 / V2 注册端点（V2 多了 phone 字段）")
    print("  3. 对比 V1 / V2 用户列表（V2 有分页参数）")
    print("  4. 试试标记为 deprecated 的 /api/v1/users-legacy")
    print("  5. 查看 GET /migration-guide 迁移指南")
    print()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
