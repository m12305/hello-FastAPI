"""
conftest.py — pytest 共享配置与 fixture

这是整个测试体系的核心：
  - 所有 test_*.py 文件中用到的 fixture 都在这里定义
  - pytest 会自动发现并加载本文件
  - 采用分层设计：engine → tables → db_session → client → auth_client

测试隔离原理：
  1. SQLite :memory: 引擎创建一次（session 级别）
  2. 每个测试函数使用独立的事务，结束即回滚
  3. get_db 依赖被覆盖为测试数据库
  4. 需要认证时，get_current_user 依赖被覆盖为假用户

fixture 层级：
  engine (session)  ← 整个测试会话只创建一次
      └─ tables (session)  ← 建表一次
          └─ db_session (function)  ← 每个测试独立事务，结束回滚
              └─ client (function)  ← TestClient + 覆盖 get_db
                  ├─ admin_client (function)  ← 覆盖为 admin 用户
                  ├─ editor_client (function)  ← 覆盖为 editor 用户
                  └─ user_client (function)  ← 覆盖为普通用户
"""

import pytest
import sys
import os

# 确保项目根目录在 sys.path 中（方便导入 main, models 等）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base, get_db
from app.auth import get_current_user
from app.models import User
from app.main import app


# ═══════════════════════════════════════════════════════════
# 第一层：数据库引擎（session 级别 —— 整个测试会话共享）
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def engine():
    """
    创建 SQLite 内存引擎 —— 整个测试会话只创建一次。

    SQLite :memory: 的特点：
      - 速度极快（无磁盘 IO）
      - 测试结束自动销毁
      - 不需要清理磁盘文件
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,  # 设为 True 可看到所有 SQL（调试用）
    )
    yield engine
    engine.dispose()


# ═══════════════════════════════════════════════════════════
# 第二层：建表（session 级别 —— 整个测试会话建一次）
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def tables(engine):
    """建表一次，所有测试共享表结构"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ═══════════════════════════════════════════════════════════
# 第三层：数据库会话（function 级别 —— 每个测试独立事务）
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def db_session(engine, tables):
    """
    每个测试使用独立的数据库事务，结束即回滚。

    这比"每个测试建表+删表"快 10 倍以上：
      - 建表/删表方案：100 个测试 ~120 秒
      - 事务回滚方案：100 个测试 ~8 秒

    原理：
      1. 开启一个数据库连接
      2. 开启一个事务
      3. 测试在这个事务中操作数据库
      4. 测试结束 → 回滚事务 → 数据库恢复干净状态
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    # 回滚事务，撤销测试中的所有数据库修改
    transaction.rollback()
    session.close()
    connection.close()


# ═══════════════════════════════════════════════════════════
# 第四层：TestClient（function 级别 —— 覆盖 get_db）
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def client(db_session):
    """
    创建 TestClient 并覆盖 get_db 依赖。

    覆盖后，所有使用 Depends(get_db) 的端点
    都会拿到 db_session（SQLite 内存库），而非真实数据库。
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # conn 和 transaction 由 db_session fixture 管理

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # 清理覆盖（重要！否则影响后续测试）
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════
# 第五层：认证客户端（覆盖 get_current_user）
# ═══════════════════════════════════════════════════════════

# ── 辅助函数：创建假用户 ──
def _make_fake_user(role: str = "user", user_id: int = 1, is_active: bool = True) -> User:
    """创建一个伪造的 User 对象（不写入数据库）"""
    return User(
        id=user_id,
        username=f"{role}_test",
        email=f"{role}@test.com",
        hashed_password="fake_hashed_password",
        role=role,
        is_active=is_active,
    )


@pytest.fixture
def admin_client(client, db_session):
    """
    以 admin 身份登录的客户端。

    覆盖 get_current_user 依赖 → 所有端点认为当前用户是 admin。
    用法:
        def test_admin_endpoint(admin_client):
            r = admin_client.get("/admin/users")
            assert r.status_code == 200
    """
    db_session.add(_make_fake_user(role="admin", user_id=99))
    db_session.commit()

    def override_get_current_user():
        return db_session.get(User, 99)

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def editor_client(client, db_session):
    """
    以 editor 身份登录的客户端。

    用法:
        def test_create_post(editor_client):
            r = editor_client.post("/posts", json={...})
            assert r.status_code == 201
    """
    db_session.add(_make_fake_user(role="editor", user_id=98))
    db_session.commit()

    def override_get_current_user():
        return db_session.get(User, 98)

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user_client(client, db_session):
    """
    以普通用户身份登录的客户端。

    用法:
        def test_user_cannot_access_admin(user_client):
            r = user_client.get("/admin/users")
            assert r.status_code == 403
    """
    db_session.add(_make_fake_user(role="user", user_id=97))
    db_session.commit()

    def override_get_current_user():
        return db_session.get(User, 97)

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════
# 辅助 fixture：通过真实登录获取 Token
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def registered_user(client):
    """
    注册一个新用户并返回其凭据。

    用法:
        def test_something(registered_user):
            username = registered_user["username"]
            password = registered_user["password"]
    """
    user_data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "test123456",
    }
    r = client.post("/register", json=user_data)
    assert r.status_code == 201
    return user_data


@pytest.fixture
def auth_token(client, registered_user):
    """
    注册 + 登录，返回 JWT Token。

    用法:
        def test_me(auth_token):
            r = client.get("/me", headers={"Authorization": f"Bearer {auth_token}"})
    """
    r = client.post("/login", json={
        "username": registered_user["username"],
        "password": registered_user["password"],
    })
    assert r.status_code == 200
    return r.json()["access_token"]
