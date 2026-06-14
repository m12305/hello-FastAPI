# 阶段 6：高级特性 — 综合 Demo

> 启动 5 个独立 Demo，交互式体验后台任务、WebSocket 聊天、生命周期管理、API 版本化、性能优化。

---

## 项目结构

```
阶段6-高级特性/
├── 6.1-后台任务/
│   └── main.py              # BackgroundTasks：发邮件、写日志、生成缩略图
│
├── 6.2-WebSocket/
│   └── main.py              # 在线聊天室：广播+私聊+在线用户列表+心跳重连
│
├── 6.3-事件钩子与生命周期/
│   └── main.py              # lifespan 管理模拟 DB/Redis，健康检查，优雅关闭
│
├── 6.4-API文档与版本化/
│   ├── main.py              # 入口：openapi_tags、servers、废弃标记
│   └── app/api/
│       ├── v1/endpoints/users.py   # V1 基础 API
│       └── v2/endpoints/users.py   # V2 升级 API（+phone +分页 +role）
│
├── 6.5-性能优化/
│   └── main.py              # N+1 vs joinedload、索引对比、sync vs async、GZip、分页
│
└── README.md                # 本文件
```

---

## 启动方式

### 通用依赖

```bash
pip install fastapi uvicorn[standard]
```

### 各 Demo 启动

| Demo | 额外依赖 | 启动命令 | 访问 |
|------|---------|---------|------|
| 6.1 后台任务 | 无 | `cd 6.1-后台任务 && uvicorn main:app --reload` | http://127.0.0.1:8000/docs |
| 6.2 WebSocket | 无 | `cd 6.2-WebSocket && uvicorn main:app --reload` | http://127.0.0.1:8000/chat |
| 6.3 生命周期 | 无 | `cd 6.3-事件钩子与生命周期 && uvicorn main:app --reload` | http://127.0.0.1:8000/docs |
| 6.4 API 版本化 | 无 | `cd 6.4-API文档与版本化 && uvicorn main:app --reload` | http://127.0.0.1:8000/docs |
| 6.5 性能优化 | `pip install sqlalchemy` | `cd 6.5-性能优化 && uvicorn main:app --reload` | http://127.0.0.1:8000/docs |

> 💡 5 个 Demo 端口独立，不能同时启动（都用 8000）。学完一个停掉再启动下一个即可。

---

## 6.1 后台任务

### 演示的端点

| 方法 | 端点 | 说明 | 观察要点 |
|------|------|------|---------|
| GET | `/` | Demo 首页，列出所有端点 | — |
| POST | `/register` | 注册（**有后台任务**）→ 秒回 | 终端输出：先看到 HTTP 响应，2 秒后才看到"邮件已发送" |
| POST | `/register-without-bg` | 注册（**无后台任务**）→ 阻塞 2-3 秒 | 对比感受响应时间差异 |
| POST | `/upload-image` | 模拟上传图片 → 后台生成缩略图 | 终端输出：3 秒后才看到"缩略图已生成" |
| GET | `/users` | 查看所有已注册用户 | — |
| GET | `/learn` | BackgroundTasks 适用场景和局限性 | 何时升级到 Celery |

### curl 快速测试

```bash
# 带后台任务的注册（立刻返回）
curl -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com"}'

# 不带后台任务的注册（阻塞 2 秒才返回——感受差异！）
curl -X POST http://127.0.0.1:8000/register-without-bg \
  -H "Content-Type: application/json" \
  -d '{"username":"test2","email":"test2@example.com"}'
```

### 知识点

- `background_tasks.add_task(func, arg1, arg2)` — 把任务丢给后台
- 响应返回**之后**才开始执行后台任务
- 适用：邮件、日志、缩略图、推送通知
- 局限：无重试、无持久化、无进度 → 复杂场景升级到 Celery

---

## 6.2 WebSocket（聊天室）

### 演示的端点

| 方式 | 端点 | 说明 |
|------|------|------|
| WebSocket | `ws://127.0.0.1:8000/ws/chat/{username}` | WebSocket 端点 |
| HTML 页面 | http://127.0.0.1:8000/chat | 聊天室页面（自动连接 WebSocket） |
| REST | GET `/online-users` | 查看在线用户列表 |
| REST | GET `/docs` | Swagger API 文档 |

### 功能说明

| 发送内容 | 效果 |
|---------|------|
| `任意消息` | 广播给所有人（`💬 用户名: 消息`） |
| `@用户名 消息` | 私聊指定用户（`🔒 XXX 悄悄对你说`） |
| `/users` | 查看在线用户列表 |

### 测试方式

```bash
# 1. 启动服务
cd 6.2-WebSocket && uvicorn main:app --reload

# 2. 打开 2-3 个浏览器标签页访问
http://127.0.0.1:8000/chat

# 3. 在标签页 A 发送 "大家好" → 所有标签页都看到
# 4. 在标签页 B 发送 "@用户123 你好" → 只有用户123 看到
# 5. 在标签页 C 发送 "/users" → 查看在线列表
# 6. 关闭标签页 A → 其他人看到 "👋 XXX 离开了聊天室"
```

### 知识点

- `@app.websocket("/ws")` → WebSocket 路由
- `await websocket.accept()` → 先接受连接
- `await websocket.receive_text()` → 接收消息
- `await websocket.send_text(data)` → 发送消息
- `ConnectionManager` 模式 → 管理所有连接
- `WebSocketDisconnect` → 处理断开

---

## 6.3 事件钩子与生命周期

### 演示的端点

| 方法 | 端点 | 说明 | 观察要点 |
|------|------|------|---------|
| GET | `/` | Demo 首页 | — |
| GET | `/health` | 健康检查（检查 DB + Redis 状态） | K8s / 负载均衡用 |
| GET | `/info` | 应用状态：启动时间、连接池大小、运行时长 | 对比启动时间和当前时间 |
| GET | `/db-test` | 测试数据库查询 | 验证 DB 连接可用 |
| POST | `/redis-test` | 写入缓存 | `{"key": "name", "value": "张三"}` |
| GET | `/redis-test/{key}` | 读取缓存 | 验证 Redis 读写 |

### 测试方式

```bash
# 1. 启动服务 —— 观察终端输出！
cd 6.3-事件钩子与生命周期 && uvicorn main:app --reload

# 终端输出：
# 🚀 应用启动中...
#   🔌 正在创建数据库连接池...
#   ✅ 数据库连接池已就绪
#   🔴 正在连接 Redis...
#   ✅ Redis 已就绪
#   ✅ 所有资源初始化完成！应用已就绪。

# 2. 测试端点
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/info
curl -X POST http://127.0.0.1:8000/redis-test \
  -H "Content-Type: application/json" \
  -d '{"key":"greeting","value":"hello"}'
curl http://127.0.0.1:8000/redis-test/greeting

# 3. 按 Ctrl+C 关闭 —— 观察优雅关闭日志！
# 👋 应用正在关闭...
#   ✅ 后台任务已取消
#   ✅ Redis 已断开
#   ✅ 数据库连接池已释放
```

### 知识点

- `lifespan` 上下文管理器 → 替代 `@app.on_event()`
- `yield` 之前 = startup，`yield` 之后 = shutdown
- `app.state.xxx` → 在请求间共享"启动时创建"的资源
- `request.app.state.xxx` → 在依赖或端点中访问

---

## 6.4 API 文档与版本化

### 演示的端点

| 方法 | 端点 | 版本 | 说明 |
|------|------|------|------|
| POST | `/api/v1/register` | V1 | 基础注册（username + email + password） |
| GET | `/api/v1/users` | V1 | 用户列表（无分页，基础字段） |
| GET | `/api/v1/users/{id}` | V1 | 用户详情 |
| POST | `/api/v2/register` | V2 | 新注册（**增加了 phone 字段**） |
| GET | `/api/v2/users` | V2 | 用户列表（**支持分页** page+size，多了 role+phone） |
| GET | `/api/v2/users/{id}` | V2 | 用户详情 |
| GET | `/api/v1/users-legacy` | V1 | ⚠️ **已废弃**（deprecated + Sunset 头） |
| GET | `/` | — | 版本概览 + 迁移指南 |
| GET | `/migration-guide` | — | V1 → V2 迁移步骤 |

### Swagger 文档特性

打开 http://127.0.0.1:8000/docs 观察：

| 特性 | 位置 |
|------|------|
| **自定义分组** | V1-用户 / V2-用户 / 系统（`openapi_tags` 控制分组和顺序） |
| **多环境切换** | 顶部下拉菜单（本地 / 测试 / 生产） |
| **废弃标记** | `/api/v1/users-legacy` 显示 ⚠️ Deprecated |
| **详细描述** | 每个端点展开后有 Markdown 格式的说明 |

### curl 快速测试

```bash
# V1 注册
curl -X POST http://127.0.0.1:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"12345678"}'

# V2 注册（多了 phone 字段）
curl -X POST http://127.0.0.1:8000/api/v2/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test2","email":"test2@example.com","password":"12345678","phone":"13800138000"}'

# V2 分页查询
curl "http://127.0.0.1:8000/api/v2/users?page=1&size=10"

# 调用已废弃接口（观察响应头中的 Deprecation + Sunset）
curl -v http://127.0.0.1:8000/api/v1/users-legacy
```

### 知识点

- URL 前缀版本化：`/api/v1/` `/api/v2/`（最推荐）
- `APIRouter(prefix="/api/v2")` → 一层层叠路径
- `openapi_tags` → 控制 Swagger 分组顺序和描述
- `deprecated=True` + Sunset 头 → 给客户端留迁移时间

---

## 6.5 性能优化

### 演示的端点

| 方法 | 端点 | 对比内容 | 观察 X-Process-Time 头 |
|------|------|---------|----------------------|
| GET | `/demo/n-plus-one` | ❌ N+1 查询（101 条 SQL） | 所有端口的响应头 |
| GET | `/demo/joinedload` | ✅ JOIN 加载（1 条 SQL） | 对比耗时差异 |
| GET | `/demo/selectinload` | ✅ IN 加载（2 条 SQL） | — |
| GET | `/demo/index-comparison` | 有索引 vs 无索引查询 | 看耗时差异 |
| GET | `/demo/sync-endpoint` | 同步 def（线程池） | 单次约 100ms |
| GET | `/demo/async-endpoint` | 异步 async def（事件循环） | 单次约 100ms |
| GET | `/demo/pagination-comparison` | 全量 vs 分页 | 看响应大小差异 |
| GET | `/demo/gzip-demo` | GZip 压缩效果 | 看 Content-Encoding: gzip |

### 依赖

```bash
pip install sqlalchemy
```

### 种子数据

启动时自动创建 100 位作者 × 5 本书 = 500 条数据，用于演示 N+1 和索引差异。

### 测试方式

```bash
# 0. 浏览器打开 DevTools → Network 标签
# 1. 对比 N+1 问题
curl -v http://127.0.0.1:8000/demo/n-plus-one 2>&1 | grep X-Process-Time
curl -v http://127.0.0.1:8000/demo/joinedload 2>&1 | grep X-Process-Time
# → joinedload 应该明显更快

# 2. 对比索引
curl http://127.0.0.1:8000/demo/index-comparison
# → 有索引的查询速度快几个数量级

# 3. 对比 sync vs async
curl -v http://127.0.0.1:8000/demo/sync-endpoint 2>&1 | grep X-Process-Time
curl -v http://127.0.0.1:8000/demo/async-endpoint 2>&1 | grep X-Process-Time

# 4. GZip 效果
curl -v http://127.0.0.1:8000/demo/gzip-demo 2>&1 | grep -E "(Content-Encoding|Content-Length)"
```

### 知识点

- N+1 问题 → `joinedload`（1 条 JOIN）或 `selectinload`（2 条 IN）
- 索引 → 经常出现在 WHERE/JOIN/ORDER BY 的列加 `index=True`
- `async def` → 不阻塞事件循环，高并发 IO 场景优势明显
- `GZipMiddleware` → 零成本压缩，文本数据减少 80%+
- 分页 → 列表接口必须分页，`page + size` 或游标分页

---

## 学习路径

```
6.1 后台任务          → 掌握 BackgroundTasks 的用法和局限
    │
    ▼
6.2 WebSocket          → 掌握双向实时通信，聊天室实战
    │
    ▼
6.3 生命周期           → 掌握 lifespan 管理应用启停和资源
    │
    ▼
6.4 API 版本化         → 掌握版本化策略和文档定制
    │
    ▼
6.5 性能优化           → 掌握定位瓶颈和优化手段（N+1、索引、分页、GZip）
```

对照文档：

- [6.1-后台任务.md](../../阶段6-高级特性/6.1-后台任务.md) — BackgroundTasks 用法、场景、局限性、Celery 升级
- [6.2-WebSocket.md](../../阶段6-高级特性/6.2-WebSocket.md) — HTTP vs WS、连接管理、广播/私聊、认证
- [6.3-事件钩子与生命周期.md](../../阶段6-高级特性/6.3-事件钩子与生命周期.md) — on_event vs lifespan、app.state、优雅关闭
- [6.4-API文档与版本化.md](../../阶段6-高级特性/6.4-API文档与版本化.md) — 文档定制、版本化策略、废弃流程
- [6.5-性能优化.md](../../阶段6-高级特性/6.5-性能优化.md) — N+1 修复、索引、sync vs async、GZip、分页

---

## 所有 Demo 的通用测试建议

1. **先用 Swagger UI**（`/docs`）了解有哪些端点
2. **观察终端输出** — 后台任务、生命周期的日志在终端而非浏览器
3. **打开浏览器 DevTools** → Network 标签 → 观察响应头（`X-Process-Time`、`Content-Encoding`）
4. **对比是学习关键** — 每个 Demo 都提供了"优化前 vs 优化后"的对比端点
