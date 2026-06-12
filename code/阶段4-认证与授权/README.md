# 阶段 4：认证与授权 — 综合 Demo

> 启动本 Demo 即可交互式体验 JWT 认证 + RBAC 权限控制 + 数据所有权 + API Key + 混合认证。

---

## 项目结构

```
阶段4-认证与授权/
├── main.py              # FastAPI 应用入口 + 全部路由（9 组端点）
├── database.py          # 引擎、SessionLocal、Base、get_db 依赖
├── models.py            # User ORM 模型（role + is_active 字段）
├── schemas.py           # Pydantic 模型（UserCreate / Token / PostCreate 等）
├── auth.py              # JWT 核心：密码哈希、Token 生成/验证、黑名单、get_current_user
├── permissions.py       # 权限层：RoleChecker、数据所有权、API Key、混合认证
└── README.md            # 本文件
```

## 启动方式

```bash
# 1. 进入目录
cd code/阶段4-认证与授权

# 2. 安装依赖
pip install sqlalchemy python-jose[cryptography] passlib[bcrypt] python-multipart

# 3. 启动服务
uvicorn main:app --reload

# 4. 打开浏览器
# http://127.0.0.1:8000/docs   — Swagger UI（推荐，支持 🔓 Authorize 一键登录）
# http://127.0.0.1:8000/redoc  — ReDoc 文档
```

## 演示的端点

### 🔐 认证（4.2 JWT）

| 方法 | 端点 | 认证方式 | 说明 |
|------|------|---------|------|
| POST | `/register` | 无 | 用户注册，密码 bcrypt 哈希后存储 |
| POST | `/login` | 表单 | OAuth2PasswordRequestForm → 返回 Access + Refresh Token |
| POST | `/refresh` | Refresh Token | 用 Refresh Token 换取新 Token 对 |
| POST | `/logout` | Bearer Token | 将当前 Token 加入黑名单，立即失效 |

### 👤 用户

| 方法 | 端点 | 权限 | 说明 |
|------|------|------|------|
| GET | `/me` | 任何登录用户 | 获取当前用户信息（`get_current_user` 依赖） |

### 🔧 管理员

| 方法 | 端点 | 权限 | 说明 |
|------|------|------|------|
| GET | `/admin/users` | admin | 查看所有用户列表（`RoleChecker(["admin"])`） |
| PATCH | `/admin/users/{id}/role` | admin | 修改用户角色（user / editor / admin） |
| PATCH | `/admin/users/{id}/toggle-active` | admin | 停用/启用用户账号 |

### 📝 文章（演示数据所有权）

| 方法 | 端点 | 权限 | 说明 |
|------|------|------|------|
| POST | `/posts/` | editor+ | 创建文章（`require_editor`） |
| GET | `/posts/` | 任何登录用户 | 文章列表 |
| GET | `/posts/{id}` | 无需登录 | 文章详情 |
| PATCH | `/posts/{id}` | 作者 或 admin | 更新文章——**非作者返回 403** |
| DELETE | `/posts/{id}` | 作者 或 admin | 删除文章——**非作者返回 403** |

### 🤖 外部 API（API Key）

| 方法 | 端点 | 认证方式 | 说明 |
|------|------|---------|------|
| GET | `/api/external/posts` | X-API-Key | 机器间通信，不需要 JWT |

### 🔄 混合认证

| 方法 | 端点 | 认证方式 | 说明 |
|------|------|---------|------|
| GET | `/hybrid/whoami` | Bearer Token **或** X-API-Key | 两种认证方式任选其一 |

## 预置测试账号

启动时自动创建，密码均为 `用户名 + 123`：

| 用户名 | 密码 | 角色 | 权限范围 |
|--------|------|------|---------|
| `admin` | `admin123` | admin | 一切权限：管理用户、修改角色、增删改文章 |
| `editor` | `editor123` | editor | 创建/修改自己的文章 |
| `user1` | `user1123` | user | 浏览文章、查看个人信息 |
| `user2` | `user2123` | user | 浏览文章、查看个人信息（已停用示例） |

## 预置 API Key

模拟外部服务调用：

| API Key | 服务名 | 权限 |
|---------|--------|------|
| `svc-a-abc123def456` | Service A | `users:read` + `posts:read` |
| `svc-b-xyz789ghi012` | Service B | `users:read` + `posts:read` + `posts:write` |

## curl 快速测试

```bash
# ═══ 1. 注册 ═══
curl -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"test123"}'

# ═══ 2. 登录 ═══
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=admin&password=admin123"
# 复制返回的 access_token，下面用 $TOKEN 代替

# ═══ 3. 获取当前用户 ═══
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/me

# ═══ 4. 权限测试：普通用户访问管理员接口 → 403 ═══
curl -H "Authorization: Bearer $USER_TOKEN" http://127.0.0.1:8000/admin/users

# ═══ 5. 所有权测试：修改别人的文章 → 403 ═══
curl -X PATCH http://127.0.0.1:8000/posts/1 \
  -H "Authorization: Bearer $OTHER_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"我想改别人的文章"}'

# ═══ 6. API Key 认证 ═══
curl -H "X-API-Key: svc-a-abc123def456" http://127.0.0.1:8000/api/external/posts

# ═══ 7. 混合认证 ═══
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/hybrid/whoami
curl -H "X-API-Key: svc-b-xyz789ghi012" http://127.0.0.1:8000/hybrid/whoami

# ═══ 8. 登出 ═══
curl -X POST http://127.0.0.1:8000/logout \
  -H "Authorization: Bearer $TOKEN"
# Token 加入黑名单，再用同一个 Token 访问会返回 401
```

## 学习路径

```
注册 → 登录(拿 Token) → /me(验证身份) → /posts(创建内容)
                                            │
                                            ├── 普通用户：只能看
                                            ├── editor：能创建/修改自己的
                                            └── admin：能管理一切 + 改角色
                                                      │
                                                      ▼
                                            /admin/users(权限控制)
                                            /admin/users/{id}/role(RBAC)
                                                      │
                                                      ▼
                                            /logout(Token 黑名单)
```

对照文档：

- [4.1-认证基础.md](../../阶段4-认证与授权/4.1-认证基础.md) — 密码哈希、Session、OAuth2 概念
- [4.2-JWT令牌认证.md](../../阶段4-认证与授权/4.2-JWT令牌认证.md) — JWT 结构、生成/验证、Token 刷新
- [4.3-权限控制.md](../../阶段4-认证与授权/4.3-权限控制.md) — RBAC、RoleChecker、API Key
- [4.4-安全最佳实践.md](../../阶段4-认证与授权/4.4-安全最佳实践.md) — HTTPS、CORS、速率限制、脱敏
