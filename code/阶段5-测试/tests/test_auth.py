"""
test_auth.py — 认证与权限测试（对应 5.1 §6 + 5.2 §4）

本文件演示：
  1. 登录成功 / 失败 / 停用用户测试
  2. 未登录访问受保护接口 → 401
  3. 携带 Token 访问受保护接口 → 200
  4. 依赖覆盖：直接用 admin_client / editor_client / user_client
  5. 权限边界测试：普通用户访问管理员接口 → 403

运行：
  pytest tests/test_auth.py -v
"""

import pytest


# ═══════════════════════════════════════════════════════════
# 登录测试
# ═══════════════════════════════════════════════════════════

class TestLogin:
    """登录功能测试"""

    def test_login_success(self, client):
        """
        正确密码登录 → 200 + access_token。

        走完整流程：先注册，再登录。
        """
        # Arrange: 注册
        client.post("/register", json={
            "username": "logintest",
            "email": "login@example.com",
            "password": "rightpassword",
        })

        # Act: 登录
        response = client.post("/login", json={
            "username": "logintest",
            "password": "rightpassword",
        })

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20  # JWT 应该有足够的长度

    def test_login_wrong_password(self, client):
        """错误密码 → 401"""
        # Arrange
        client.post("/register", json={
            "username": "wrongpwd_test",
            "email": "wrong@example.com",
            "password": "rightpassword",
        })

        # Act: 用错误密码登录
        response = client.post("/login", json={
            "username": "wrongpwd_test",
            "password": "wrongpassword",
        })

        # Assert
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在的用户 → 401"""
        response = client.post("/login", json={
            "username": "nobody",
            "password": "whatever",
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """
        停用用户 → 403。

        这里演示直接操作 db_session 来创建停用用户。
        无需走注册流程，直接插入数据库。
        """
        from models import User
        from auth import get_password_hash

        # Arrange: 直接在数据库中创建一个停用用户
        user = User(
            username="disabled_user",
            email="disabled@x.com",
            hashed_password=get_password_hash("test123456"),
            role="user",
            is_active=False,  # ← 已停用
        )
        db_session.add(user)
        db_session.commit()

        # Act: 尝试登录
        response = client.post("/login", json={
            "username": "disabled_user",
            "password": "test123456",
        })

        # Assert
        assert response.status_code == 403
        assert "停用" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════
# 受保护接口测试（5.1 §6）
# ═══════════════════════════════════════════════════════════

class TestProtectedRoutes:
    """需要认证的接口测试"""

    def test_without_token_returns_401(self, client):
        """
        不带 Token 访问需要认证的接口 → 401。

        PATCH /users/1 需要 get_current_user 依赖，
        不提供 Token 应该返回 401。
        """
        response = client.patch("/users/1", json={"username": "hack"})
        assert response.status_code == 401

    def test_with_token_returns_200(self, client):
        """
        携带正确 Token → 200。

        演示完整的 注册→登录→携带Token访问 流程。
        """
        # 注册 + 登录
        client.post("/register", json={
            "username": "token_test",
            "email": "token_test@x.com",
            "password": "testpass123",
        })
        login_r = client.post("/login", json={
            "username": "token_test", "password": "testpass123"
        })
        token = login_r.json()["access_token"]

        # 获取用户 ID
        users = client.get("/users").json()
        my_id = [u for u in users if u["username"] == "token_test"][0]["id"]

        # 带 Token 更新自己的信息
        response = client.patch(
            f"/users/{my_id}",
            json={"username": "new_name"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["username"] == "new_name"

    def test_invalid_token_format(self, client):
        """格式错误的 Token → 401"""
        response = client.patch(
            "/users/1",
            json={"username": "hack"},
            headers={"Authorization": "NotBearer blahblah"},
        )
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════
# 权限控制测试 —— 使用依赖覆盖（5.2 §4）
# ═══════════════════════════════════════════════════════════

class TestPermissionWithOverrides:
    """
    通过 fixture 覆盖 get_current_user 来测试权限。

    这种方式的好处：
      - 不需要真实注册 + 登录 + 拿到 Token
      - 直接模拟不同角色的用户
      - 测试更关注"权限逻辑"而非"认证流程"
    """

    def test_admin_can_access_admin_endpoint(self, admin_client):
        """
        admin 访问 /admin/users → 200。

        admin_client fixture 覆盖了 get_current_user，
        使请求以 admin 身份执行。
        """
        response = admin_client.get("/admin/users")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_editor_cannot_access_admin_endpoint(self, editor_client):
        """
        editor 访问管理员接口 → 403。

        即使已登录，角色不对也不能访问。
        """
        response = editor_client.get("/admin/users")
        assert response.status_code == 403

    def test_normal_user_cannot_access_admin_endpoint(self, user_client):
        """
        普通用户访问管理员接口 → 403。
        """
        response = user_client.get("/admin/users")
        assert response.status_code == 403

    def test_editor_can_create_post(self, editor_client):
        """
        editor 可以创建文章 → 201。
        """
        response = editor_client.post("/posts", json={
            "title": "编辑的文章",
            "content": "这是一篇测试文章。",
        })
        assert response.status_code == 201
        assert response.json()["title"] == "编辑的文章"

    def test_normal_user_cannot_create_post(self, user_client):
        """
        普通用户不能创建文章 → 403（需要 editor+ 角色）。
        """
        response = user_client.post("/posts", json={
            "title": "不应该成功",
            "content": "我没有权限创建文章。",
        })
        assert response.status_code == 403

    def test_admin_can_update_role(self, admin_client, db_session):
        """
        admin 可以修改用户角色 → 200。
        """
        # Arrange: 先创建一个用户
        from models import User
        from auth import get_password_hash

        user = User(
            username="role_target",
            email="role_target@x.com",
            hashed_password=get_password_hash("test123"),
            role="user",
        )
        db_session.add(user)
        db_session.commit()

        # Act: admin 把这个用户改为 editor
        response = admin_client.patch(
            f"/admin/users/{user.id}/role",
            json={"role": "editor"},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["role"] == "editor"


# ═══════════════════════════════════════════════════════════
# 文章所有权测试
# ═══════════════════════════════════════════════════════════

class TestPostOwnership:
    """文章数据所有权测试"""

    def test_author_can_update_own_post(self, editor_client, db_session):
        """
        作者可以更新自己的文章 → 200。
        """
        from models import Post

        # 先让 editor_client 对应的假用户有 id
        # editor_client 用的是 user_id=98 的假用户
        post = Post(
            title="我的文章",
            content="这是我的文章内容。",
            user_id=98,  # ← editor_client 的假用户 id
        )
        db_session.add(post)
        db_session.commit()

        response = editor_client.patch(
            f"/posts/{post.id}",
            json={"title": "更新后的标题"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "更新后的标题"

    def test_non_author_cannot_update_post(self, user_client, db_session):
        """
        非作者不能更新别人的文章 → 403。

        user_client 使用 user_id=97，尝试修改 user_id=1 的文章。
        """
        from models import Post

        # 创建一篇属于另一个用户的文章
        post = Post(
            title="别人的文章",
            content="你不能修改这篇文章。",
            user_id=1,  # ← 不属于 user_client (user_id=97)
        )
        db_session.add(post)
        db_session.commit()

        response = user_client.patch(
            f"/posts/{post.id}",
            json={"title": "尝试篡改"},
        )
        assert response.status_code == 403

    def test_admin_can_delete_any_post(self, admin_client, db_session):
        """
        admin 可以删除任何人的文章 → 200。
        """
        from models import Post

        # 创建一篇属于某个普通用户的文章
        post = Post(
            title="普通用户的文章",
            content="admin 可以删除这篇文章。",
            user_id=50,  # ← 不是 admin 的文章
        )
        db_session.add(post)
        db_session.commit()

        response = admin_client.delete(f"/posts/{post.id}")
        assert response.status_code == 200
