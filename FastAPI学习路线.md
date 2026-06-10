# FastAPI 学习路线：从零到企业级项目开发

> 本路线覆盖从 Python 基础回顾到企业级项目实战的完整路径。
> 学习每个章节时，请严格按照 `FastAPI学习方法.md` 中的六步法执行。

---

## 路线总览

```mermaid
graph LR
    A[阶段0: 前置基础] --> B[阶段1: FastAPI 核心]
    B --> C[阶段2: 请求与响应]
    C --> D[阶段3: 数据库与ORM]
    D --> E[阶段4: 认证与授权]
    E --> F[阶段5: 测试]
    F --> G[阶段6: 高级特性]
    G --> H[阶段7: 架构设计]
    H --> I[阶段8: 部署运维]
    I --> J[阶段9: 实战项目]
```

| 阶段 | 主题 | 章节数 | 建议时长 |
|------|------|--------|---------|
| 0 | 前置基础 | 4 章 | 1-2 周 |
| 1 | FastAPI 核心 | 5 章 | 1-2 周 |
| 2 | 请求与响应 | 5 章 | 1-2 周 |
| 3 | 数据库与 ORM | 5 章 | 2-3 周 |
| 4 | 认证与授权 | 4 章 | 1-2 周 |
| 5 | 测试 | 3 章 | 1 周 |
| 6 | 高级特性 | 5 章 | 2-3 周 |
| 7 | 架构设计 | 4 章 | 1-2 周 |
| 8 | 部署运维 | 4 章 | 1-2 周 |
| 9 | 实战项目 | 3 个项目 | 3-6 周 |
| **合计** | | **39 章 + 3 项目** | **3-6 个月** |

---

## 阶段 0：前置基础（打牢地基）

> ⚠️ **重要**：如果你已经熟悉 Python 类型标注、async/await 和 HTTP 协议，可以快速过一遍，直接进入阶段 1。

### 第 0.1 章：Python 类型标注（Type Hints）

FastAPI 的核心机制依赖于 Python 类型标注，这是必须扎实掌握的基础。

- `typing` 模块：`List`, `Dict`, `Tuple`, `Set`, `Optional`, `Union`, `Any`
- Python 3.10+ 新语法：`list[int]`, `dict[str, int]`, `X | None`
- `Literal` 类型与枚举约束
- `dataclass` 与 `Pydantic` 的关系
- `Annotated` 类型（FastAPI 推荐方式）

**实战练习：** 用类型标注改写一个自己之前写过的 Python 脚本

---

### 第 0.2 章：异步编程基础

FastAPI 是一个异步框架，理解 `async/await` 至关重要。

- 并发 vs 并行：理解 `threading` vs `asyncio`
- 协程（Coroutine）：`async def` / `await`
- 事件循环（Event Loop）：`asyncio.run()`, `asyncio.gather()`
- 异步上下文管理器：`async with`
- 常见陷阱：不要在协程中调用同步阻塞函数

**实战练习：** 并发请求 10 个 URL，对比同步 vs 异步耗时

---

### 第 0.3 章：HTTP 协议基础

- HTTP 方法：GET / POST / PUT / PATCH / DELETE
- 状态码：2xx 成功 / 3xx 重定向 / 4xx 客户端错误 / 5xx 服务端错误
- 请求头与响应头：Content-Type, Authorization, Accept
- URL 结构：路径参数 vs 查询参数
- RESTful API 设计原则

**实战练习：** 用浏览器 DevTools 分析 3 个你常用网站的 API 请求

---

### 第 0.4 章：Pydantic 基础

FastAPI 的数据验证核心是 Pydantic，提前熟悉它会让你事半功倍。

- `BaseModel`：定义数据模型
- 字段类型与验证：`Field()`, `validator`, `model_validator`
- 嵌套模型：模型的组合与继承
- JSON Schema：Pydantic 如何自动生成 Schema
- `model_dump()` / `model_validate()`

**实战练习：** 定义一个包含嵌套结构的数据模型，验证非法数据被正确拒绝

---

## 阶段 1：FastAPI 核心（初识框架）

### 第 1.1 章：Hello World — 第一个 FastAPI 应用

- 安装：`pip install fastapi uvicorn[standard]`
- 最小应用：3 行代码启动一个 API
- Uvicorn：ASGI 服务器的角色
- 热重载：`--reload` 开发模式
- 自动生成的 OpenAPI 文档：`/docs` (Swagger UI) 和 `/redoc`

**实战练习：** 创建一个返回当前时间的 API

---

### 第 1.2 章：路径操作（Path Operations）

- 路由装饰器：`@app.get()`, `@app.post()`, `@app.put()`, `@app.delete()`, `@app.patch()`
- 路径参数：`@app.get("/items/{item_id}")`
- 路径参数的枚举约束
- 路径操作装饰器的参数顺序
- `@app.api_route()`：自定义 HTTP 方法

**实战练习：** 创建一个 CRUD 路由骨架（用户管理 4 个端点）

---

### 第 1.3 章：查询参数与请求体

- 查询参数：函数参数中非路径参数的默认值
- 可选参数 vs 必选参数
- 请求体：Pydantic 模型作为参数
- 多请求体参数：`Body(embed=True)` 的使用场景
- 路径参数 + 查询参数 + 请求体的组合

**实战练习：** 实现一个带分页和过滤的列表查询接口

---

### 第 1.4 章：响应模型与状态码

- `response_model` 参数：控制输出数据结构
- `response_model_exclude` / `response_model_include`：过滤字段
- `status_code`：设置默认状态码
- `Response` 对象：手动构建响应
- 常用响应类型：`JSONResponse`, `HTMLResponse`, `FileResponse`, `StreamingResponse`

**实战练习：** 创建同一个数据的"公开视图"和"详情视图"两个接口

---

### 第 1.5 章：错误处理

- `HTTPException`：抛出标准 HTTP 错误
- 自定义异常处理器：`@app.exception_handler`
- 全局异常捕获与统一错误格式
- 请求验证错误的定制
- 404 vs 422 vs 500 的正确使用场景

**实战练习：** 为你的 API 设计统一的错误响应格式 `{"error": "...", "detail": "...", "code": "..."}`

---

## 阶段 2：请求与响应（深入细节）

### 第 2.1 章：请求数据的高级验证

- `Query()`：字符串长度、正则、别名
- `Path()`：路径参数的数据校验
- `Field()`：模型字段的高级校验
- Pydantic v2 的 `field_validator` 与 `model_validator`
- 自定义验证装饰器

**实战练习：** 实现一个用户注册接口，包含手机号、邮箱、密码强度的完整校验

---

### 第 2.2 章：请求头、Cookie 与表单

- `Header()`：读取请求头
- `Cookie()`：读取 Cookie
- `Form()`：处理表单提交（OAuth2 密码模式的基础）
- `File()` 与 `UploadFile`：文件上传
- 多文件上传与表单+文件混合

**实战练习：** 实现一个文件上传接口，支持图片类型校验和大小限制

---

### 第 2.3 章：依赖注入（Dependency Injection）

> ⚡ **这是 FastAPI 最重要的概念之一，多花时间消化。**

- `Depends()`：依赖注入的基本语法
- 依赖的复用：多个路径操作共享同一依赖
- 依赖的嵌套：一个依赖可以依赖另一个
- 依赖作为函数参数 vs 路径装饰器依赖
- 带 yield 的依赖：`yield` 实现资源的获取与释放（数据库连接、文件句柄）
- 类作为依赖：`__call__` 方法

**实战练习：** 用依赖注入实现请求日志记录、用户认证检查、数据库会话管理

---

### 第 2.4 章：中间件与 CORS

- 中间件机制：请求 → 中间件 → 路由 → 中间件 → 响应
- `@app.middleware("http")`：自定义中间件
- 请求计时、请求 ID 注入、全局异常捕获
- CORS 中间件：`CORSMiddleware` 配置详解
- 中间件的执行顺序
- TrustedHostMiddleware, GZipMiddleware 等内置中间件

**实战练习：** 编写一个中间件，为每个请求添加 `X-Process-Time` 响应头

---

### 第 2.5 章：静态文件与模板

- `StaticFiles`：挂载静态资源目录
- Jinja2 模板引擎集成
- `HTMLResponse` 返回模板渲染的页面
- 前后端不分离的简单应用模板

**实战练习：** 搭建一个简单的后台管理页面，展示 API 数据

---

## 阶段 3：数据库与 ORM（持久化存储）

### 第 3.1 章：SQLAlchemy 基础

- ORM 概念：为什么要用 ORM？
- SQLAlchemy 1.4+ 与 2.0 的差异
- 定义模型：`Base`, `Mapped`, `mapped_column`
- 引擎与会话：`create_engine`, `Session`, `sessionmaker`
- CRUD 操作：增删改查的标准写法

**实战练习：** 创建一个 User 模型并完成 CRUD 操作

---

### 第 3.2 章：SQLAlchemy + FastAPI 集成

- 使用依赖注入管理数据库会话（`yield` 模式）
- 请求-响应生命周期中的会话管理
- Pydantic 模型 vs SQLAlchemy 模型的分离
- `relationship` 与关联查询
- Eager Loading vs Lazy Loading

**实战练习：** 实现文章（Post）和用户（User）的一对多关联查询

---

### 第 3.3 章：Alembic 数据库迁移

- Alembic 是什么？为什么需要它？
- 初始化：`alembic init`
- 生成迁移：`alembic revision --autogenerate`
- 执行迁移：`alembic upgrade head`
- 回滚：`alembic downgrade -1`
- 生产环境的迁移最佳实践

**实战练习：** 为你的数据库添加一个新字段，用 Alembic 完成迁移

---

### 第 3.4 章：异步数据库操作

- `sqlalchemy.ext.asyncio`：AsyncEngine, AsyncSession
- `asyncpg` vs `psycopg2`
- 异步与同步的区别：何时用哪个？
- 异步查询语句的写法：`select()`, `execute()`
- 连接池配置与优化

**实战练习：** 将同步数据库操作改写为异步版本，对比性能

---

### 第 3.5 章：数据库高级话题

- 索引设计与查询优化
- 事务管理：`commit`, `rollback`
- N+1 查询问题与解决方案
- 分页的通用实现（offset / cursor 分页）
- 软删除（Soft Delete）模式
- 通用 Repository 模式封装

**实战练习：** 实现一个通用的分页工具函数和 Repository 基类

---

## 阶段 4：认证与授权（安全防护）

### 第 4.1 章：认证基础

- 认证 vs 授权的区别
- HTTP Basic Auth：原理与局限
- Token 认证概览：JWT vs Session
- OAuth2 协议基础：角色与流程
- 密码哈希：`passlib` + `bcrypt`

**实战练习：** 实现基于 Session 的简单登录/登出

---

### 第 4.2 章：JWT 令牌认证

- JWT 结构：Header.Payload.Signature
- 生成与验证 JWT：`python-jose`
- Access Token vs Refresh Token
- Token 过期策略与刷新流程
- JWT 在 FastAPI 中的依赖注入封装
- `OAuth2PasswordBearer` + `OAuth2PasswordRequestForm`

**实战练习：** 实现完整的用户注册 → 登录 → 获取 Token → 访问受保护接口 流程

---

### 第 4.3 章：权限控制

- 基于角色的访问控制（RBAC）
- 权限装饰器：`@requires_role("admin")`
- 依赖注入实现权限校验
- API Key 认证（用于机器间通信）
- 多认证方式共存

**实战练习：** 实现普通用户 / 管理员 / 超级管理员的角色权限体系

---

### 第 4.4 章：安全最佳实践

- HTTPS 强制与 HSTS
- CSRF 防护
- CORS 安全配置
- 速率限制（Rate Limiting）
- 敏感数据脱敏（response_model 过滤）
- 安全响应头：X-Content-Type-Options, X-Frame-Options 等

**实战练习：** 为你的 API 进行安全审计并加固

---

## 阶段 5：测试（质量保障）

### 第 5.1 章：使用 TestClient 编写测试

- `TestClient`：基于 `httpx` 的同步测试客户端
- 测试 fixture：`@pytest.fixture` 管理测试依赖
- 测试数据库：使用 SQLite 内存库隔离测试
- 覆盖所有 HTTP 方法的测试

**实战练习：** 为阶段 1 的所有接口写测试用例

---

### 第 5.2 章：依赖覆盖与 Mock

- `app.dependency_overrides`：替换测试环境中的依赖
- Mock 外部服务：支付、邮件、第三方 API
- 测试认证接口：模拟登录状态
- 参数化测试：`@pytest.mark.parametrize`

**实战练习：** Mock 一个外部短信服务依赖，测试用户注册流程

---

### 第 5.3 章：测试策略与 CI

- 测试金字塔：单元测试 > 集成测试 > E2E 测试
- 代码覆盖率：`coverage.py` + `pytest-cov`
- GitHub Actions / GitLab CI 自动化测试
- 测试文档与代码评审

**实战练习：** 为项目配置 GitHub Actions，实现推送自动测试

---

## 阶段 6：高级特性（进阶提升）

### 第 6.1 章：后台任务

- `BackgroundTasks`：请求响应后执行的轻量任务
- 适用场景：发送邮件、写日志、推送通知
- 后台任务的局限性（无重试、无持久化）
- 何时升级到 Celery / ARQ 等任务队列

**实战练习：** 实现注册后发送欢迎邮件（后台任务 + 日志记录）

---

### 第 6.2 章：WebSocket

- WebSocket vs HTTP 请求-响应模式的对比
- `@app.websocket()`：WebSocket 路由
- 连接管理与心跳检测
- 简单的聊天室实现
- 广播与私聊的消息模式

**实战练习：** 实现一个简易的多人在线聊天室

---

### 第 6.3 章：事件钩子与生命周期

- `@app.on_event("startup")` / `@app.on_event("shutdown")`
- `lifespan` 上下文管理器（新版推荐方式）
- 应用启动时的初始化：数据库连接池、缓存连接
- 优雅关闭：释放资源、等待任务完成

**实战练习：** 用 lifespan 管理 Redis 连接的创建与释放

---

### 第 6.4 章：API 文档与版本化

- 自定义 OpenAPI Schema
- Swagger UI 美化与定制
- API 版本化策略：
  - URL 前缀：`/api/v1/`, `/api/v2/`
  - 请求头：`Accept: application/vnd.myapi.v1+json`
  - 查询参数：`/items/?version=1`
- 路由前缀与 APIRouter 版本组织
- API 废弃与 Sunset 策略

**实战练习：** 为 API 设计 v1/v2 两个版本，实现共存与渐进式迁移

---

### 第 6.5 章：性能优化

- 异步 vs 同步的性能对比
- 数据库查询优化：索引、连接池、查询缓存
- 响应缓存：`Cache-Control` 头
- 分页与字段过滤（减少传输数据量）
- 使用 `asyncpg` 连接池的调优
- 压测工具：使用 `wrk` 或 `locust` 进行压力测试

**实战练习：** 对 API 进行压力测试，定位瓶颈并优化

---

## 阶段 7：架构设计（工程化思维）

### 第 7.1 章：项目结构设计

- 小型项目 vs 大型项目的目录结构
- 推荐的大项目结构：

```
project/
├── app/
│   ├── api/          # 路由层
│   │   └── v1/
│   ├── core/         # 配置、安全、依赖
│   ├── crud/         # 数据库操作
│   ├── db/           # 数据库模型、会话、迁移
│   ├── models/       # Pydantic 模型（Schema）
│   ├── services/     # 业务逻辑
│   ├── utils/        # 工具函数
│   └── main.py       # 应用入口
├── tests/
├── alembic/
├── requirements.txt
└── Dockerfile
```

- APIRouter：模块化路由组织
- 配置管理：`pydantic-settings` 环境变量管理
- 常量、异常、日志的统一管理

**实战练习：** 将之前写的杂乱的 API 重构为规范的项目结构

---

### 第 7.2 章：配置管理

- `pydantic-settings`：类型安全的配置
- 多环境配置：开发 / 测试 / 生产
- `.env` 文件管理敏感信息
- 配置的依赖注入：全局获取配置的优雅方式
- 12-Factor App 配置原则

**实战练习：** 为项目配置开发、测试、生产三套环境

---

### 第 7.3 章：日志系统

- Python `logging` 模块深度使用
- 结构化日志：`structlog` 或自定义 JSON 格式
- 请求/响应日志中间件
- 日志分级：DEBUG / INFO / WARNING / ERROR / CRITICAL
- 生产环境日志收集：ELK / Loki 概述

**实战练习：** 实现结构化日志，记录每个请求的 method、path、status、耗时

---

### 第 7.4 章：缓存策略

- 响应缓存：`Cache-Control` / `ETag` / `Last-Modified`
- 内存缓存：`cachetools` 或自定义 dict
- Redis 缓存集成
- 缓存模式：Cache-Aside, Read-Through, Write-Through
- 缓存失效策略与缓存雪崩预防

**实战练习：** 用 Redis 为热门数据接口添加 5 分钟缓存

---

## 阶段 8：部署运维（上线准备）

### 第 8.1 章：Docker 容器化

- `Dockerfile` 编写：多阶段构建优化镜像体积
- `docker-compose.yml`：编排 FastAPI + PostgreSQL + Redis
- `.dockerignore` 与镜像体积优化
- 健康检查：`HEALTHCHECK` 指令
- 非 root 用户运行

**实战练习：** 为项目编写 `Dockerfile` 和 `docker-compose.yml`，一键启动全套服务

---

### 第 8.2 章：CI/CD 流水线

- GitHub Actions 工作流编排
- 自动测试 + 代码检查（lint）
- 自动构建 Docker 镜像
- 自动部署到服务器
- 蓝绿部署 / 滚动更新策略概述

**实战练习：** 配置 GitHub Actions，实现 push → test → build → deploy 全流程

---

### 第 8.3 章：生产部署

- Gunicorn + Uvicorn Worker 模式
- Nginx 反向代理配置
- HTTPS 证书（Let's Encrypt / Certbot）
- 进程管理：systemd / Supervisor
- 云平台部署概览：AWS / GCP / 阿里云 / Vercel + Railway

**实战练习：** 在云服务器上完成一次完整部署

---

### 第 8.4 章：监控与运维

- 健康检查端点：`/health`, `/ready`
- Prometheus + Grafana 指标监控
- Sentry 错误追踪集成
- API 调用量统计与分析
- 告警策略与 on-call

**实战练习：** 为 API 接入 Sentry 错误追踪

---

## 阶段 9：实战项目（融会贯通）

> 以下三个项目难度递增，建议按顺序完成。

### 项目 1：Todo API（入门级 | 1-2 周）

完整的待办事项管理系统。

**功能需求：**
- 用户注册/登录（JWT）
- 创建/编辑/删除/完成 Todo
- Todo 分类（标签）
- 按状态/标签筛选
- 用户只能看到自己的 Todo

**技术栈：** FastAPI + SQLAlchemy + JWT + SQLite/PostgreSQL
**涵盖知识点：** 阶段 0-4 全部内容

---

### 项目 2：博客系统 API（中等级 | 2-3 周）

一个完整的内容管理系统后端。

**功能需求：**
- 用户系统（普通用户 / 作者 / 管理员）
- 文章的 CRUD + 草稿/发布状态
- Markdown 文章内容
- 评论系统（支持嵌套回复）
- 点赞/收藏
- 全文搜索
- 文章标签与分类
- 图片上传（头像、文章配图）
- API 速率限制
- 后台管理统计接口

**技术栈：** FastAPI + SQLAlchemy + Alembic + Redis + Celery + Docker
**涵盖知识点：** 阶段 0-7 全部内容

---

### 项目 3：电商 API（企业级 | 3-4 周）

一个简化的电商平台后端，接近生产环境标准。

**功能需求：**
- 用户系统（买家 / 卖家 / 管理员）
- 商品管理（创建/上架/下架/库存）
- 商品分类与属性（规格、SKU）
- 购物车
- 订单系统（创建 → 支付 → 发货 → 确认收货 → 完成）
- 支付集成（模拟第三方支付回调）
- 库存扣减与事务处理
- 优惠券系统
- 地址管理
- 评价系统
- 简单的推荐（基于购买记录）
- 后台数据看板

**技术栈：**
- FastAPI（异步）
- PostgreSQL + SQLAlchemy 2.0 async
- Redis（缓存 + 分布式锁）
- Celery（异步任务：订单超时取消）
- Docker + Docker Compose
- Nginx 反向代理
- GitHub Actions CI/CD
- Sentry 错误追踪
- Prometheus 指标暴露

**涵盖知识点：** 全部阶段（0-8）

---

## 推荐学习资源

### 官方文档（必读）
- [FastAPI 官方文档](https://fastapi.tiangolo.com) — 框架作者的教程，质量极高
- [Pydantic V2 文档](https://docs.pydantic.dev/latest/) — 数据验证核心
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/) — ORM 参考

### 书籍推荐
- 《FastAPI: Modern Python Web Development》— Bill Lubanovic
- 《Building Data Science Applications with FastAPI》— François Voron
- 《Fluent Python》— Luciano Ramalho（Python 进阶经典）

### 视频课程
- FastAPI 官方作者 [tiangolo 的教程视频](https://www.youtube.com/@tiangolo)
- freeCodeCamp FastAPI 教程

### 开源项目参考
- [Full Stack FastAPI Template](https://github.com/tiangolo/full-stack-fastapi-template) — 官方全栈模板
- [FastAPI Best Architecture](https://github.com/fastapi-practices/fastapi_best_architecture) — 企业级项目结构参考

---

> 🎯 **下一步：** 打开 `FastAPI学习方法.md` 了解学习方法，然后从阶段 0.1 开始你的学习之旅！
