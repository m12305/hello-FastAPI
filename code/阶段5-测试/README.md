# 阶段 5：测试 — 综合 Demo

> 不靠 Postman 逐一点、不靠 curl 手动测——用 FastAPI TestClient + pytest 为后端 API 编写自动化测试，跑完只需 3 秒。

---

## 项目结构

```
阶段5-测试/
├── app/                     # 🎯 业务代码（"被测系统"）
│   ├── main.py              #   FastAPI 应用入口
│   ├── database.py          #   数据库配置（SQLAlchemy 2.0）
│   ├── models.py            #   ORM 模型（User + Post）
│   ├── schemas.py           #   Pydantic 数据校验
│   ├── auth.py              #   JWT 认证 + 角色检查依赖
│   └── routers/             #   路由模块
│       ├── users.py         #     用户 + 认证 + 管理员端点
│       └── posts.py         #     文章 CRUD + 外部服务 Mock 演示
│
├── tests/                   # 🧪 测试目录（与 app/ 平级）
│   ├── conftest.py          #   共享 fixture（引擎 / 会话 / 认证客户端）
│   ├── test_users.py        #   用户 CRUD 测试 + 参数化测试 + 边界值测试
│   ├── test_auth.py         #   认证测试 + 权限控制测试 + 依赖覆盖
│   └── test_mock.py         #   Mock 测试（MagicMock / AsyncMock / patch）
│
├── .github/workflows/
│   └── ci.yml.example       # GitHub Actions CI 配置示例
│
├── run_tests.bat            # Windows 一键运行所有测试
└── README.md                # 本文件
```

---

## 启动方式

### 1. 安装依赖

```bash
# 应用依赖
pip install fastapi uvicorn[standard] sqlalchemy python-jose[cryptography] passlib[bcrypt]

# 测试依赖
pip install httpx pytest pytest-cov
```

### 2. 启动应用（可选——查看被测系统）

```bash
cd code/阶段5-测试
uvicorn app.main:app --reload
# 浏览器打开 http://127.0.0.1:8000/docs
```

### 3. 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 只运行用户测试
pytest tests/test_users.py -v

# 运行特定测试关键字
pytest tests/ -v -k "login"

# 带覆盖率
pytest tests/ --cov=. --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest tests/ --cov=. --cov-report=html
# 然后打开 htmlcov/index.html
```

---

## 被测试的端点

### 🔐 认证

| 方法 | 端点 | 说明 | 测试覆盖 |
|------|------|------|----------|
| POST | `/register` | 用户注册 | ✅ 正常 / 重复用户名 / 非法参数 |
| POST | `/login` | 用户登录 | ✅ 正确密码 / 错误密码 / 不存在用户 / 停用用户 |

### 👤 用户

| 方法 | 端点 | 认证 | 说明 | 测试覆盖 |
|------|------|------|------|---------|
| GET | `/users` | 无 | 用户列表 | ✅ 返回列表 |
| GET | `/users/{id}` | 无 | 用户详情 | ✅ 存在 / 不存在 |
| PATCH | `/users/{id}` | JWT | 更新用户 | ✅ 更新自己 / 更新别人→403 |
| DELETE | `/users/{id}` | JWT | 删除用户 | ✅ 删除自己 / 删除后查不到 |

### 🔧 管理员

| 方法 | 端点 | 认证 | 说明 | 测试覆盖 |
|------|------|------|------|---------|
| GET | `/admin/users` | admin | 所有用户列表 | ✅ admin→200 / editor→403 / user→403 |
| PATCH | `/admin/users/{id}/role` | admin | 修改角色 | ✅ 成功修改 |

### 📝 文章

| 方法 | 端点 | 认证 | 说明 | 测试覆盖 |
|------|------|------|------|---------|
| POST | `/posts` | editor+ | 创建文章 | ✅ editor→201 / user→403 |
| GET | `/posts` | 无 | 文章列表 | ✅ 返回列表 |
| GET | `/posts/{id}` | 无 | 文章详情 | ✅ 存在 |
| PATCH | `/posts/{id}` | JWT | 更新文章 | ✅ 作者 / 非作者→403 / admin 可改任何人 |
| DELETE | `/posts/{id}` | JWT | 删除文章 | ✅ admin 可删任何人的 |

### 🌤 外部服务

| 方法 | 端点 | 说明 | 测试覆盖 |
|------|------|------|----------|
| GET | `/weather?city=北京` | 模拟调用外部天气 API | ✅ Mock 成功 / Mock 超时 |

---

## 预置测试账号

启动应用时自动创建（种子数据）：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | admin |
| `editor` | `editor123` | editor |
| `user1` | `user1123` | user |
| `user2` | `user2123` | user |

---

## 测试文件对照

| 文件 | 对应章节 | 核心知识点 |
|------|---------|-----------|
| `test_users.py` | 5.1 | TestClient CRUD、AAA 模式、参数化、边界值 |
| `test_auth.py` | 5.1 §6 + 5.2 §4 | 认证流程测试、权限控制、依赖覆盖（admin/editor/user_客户端） |
| `test_mock.py` | 5.2 | MagicMock、AsyncMock、side_effect、unittest.mock.patch |
| `conftest.py` | 5.1 §4 + 5.2 §2 | fixture 分层设计、事务回滚隔离、依赖覆盖 |
| `ci.yml.example` | 5.3 §3 | GitHub Actions 配置（lint → test → coverage） |

---

## 关键设计

### 1. 事务回滚隔离（conftest.py）

```
每个测试函数：
  1. 开启连接 + 事务
  2. 测试执行（在干净数据库中读写）
  3. 事务回滚 → 数据库恢复干净状态

效果：100 个测试从 ~120 秒 → ~8 秒
```

### 2. 认证客户端 fixture

```python
# 不需要真实登录就能测试权限！
def test_admin_endpoint(admin_client):
    r = admin_client.get("/admin/users")
    assert r.status_code == 200
```

### 3. Mock 外部服务

```python
# 不调真实 API，不发短信，不花钱
with patch("main.fetch_weather_from_external", new_callable=AsyncMock) as mock_fn:
    mock_fn.return_value = {"temperature": 25}
    response = client.get("/weather")
    assert response.json()["temperature"] == 25
```

---

## 学习路径

```
1. 先读懂 app/main.py       → 了解"被测系统"有哪些端点
2. 再看 tests/conftest.py   → 理解测试基础设施怎么搭的
3. 跑 test_users.py         → 掌握 TestClient 基本测试写法
4. 跑 test_auth.py          → 掌握权限测试和依赖覆盖
5. 跑 test_mock.py          → 掌握 Mock 外部服务
6. 看 ci.yml.example        → 了解 CI 怎么配
```

对照文档：

- [5.1-使用TestClient编写测试.md](../../阶段5-测试/5.1-使用TestClient编写测试.md)
- [5.2-依赖覆盖与Mock.md](../../阶段5-测试/5.2-依赖覆盖与Mock.md)
- [5.3-测试策略与CI.md](../../阶段5-测试/5.3-测试策略与CI.md)
