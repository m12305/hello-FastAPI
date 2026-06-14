"""
test_users.py — 用户 CRUD 测试（对应 5.1 TestClient 基础）

本文件演示：
  1. TestClient 的基本用法（get / post / patch / delete）
  2. 状态码断言（200 / 201 / 400 / 404 / 422）
  3. JSON 响应断言（字段存在、字段值、字段类型）
  4. AAA 模式（Arrange → Act → Assert）
  5. 参数化测试（@pytest.mark.parametrize）
  6. 边界值测试（最小值、最大值、刚好超出）

运行：
  pytest tests/test_users.py -v
"""

import pytest


# ═══════════════════════════════════════════════════════════
# 注册测试
# ═══════════════════════════════════════════════════════════

class TestRegister:
    """用户注册相关测试（按功能分组用 Test 类）"""

    def test_register_success(self, client):
        """
        正常注册 → 201，返回用户信息（不含密码）。

        AAA 模式:
          Arrange: 准备注册数据
          Act: POST /register
          Assert: 检查状态码、字段存在性和类型
        """
        # Arrange
        user_data = {
            "username": "zhangsan",
            "email": "zhang@example.com",
            "password": "secret123",
        }

        # Act
        response = client.post("/register", json=user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "zhangsan"
        assert data["email"] == "zhang@example.com"
        assert "id" in data            # 应该有自动生成的 ID
        assert isinstance(data["id"], int)  # ID 应该是整数
        assert "password" not in data  # 绝对不能返回密码！
        assert "hashed_password" not in data  # 哈希也不能返回！

    def test_register_duplicate_username(self, client):
        """重复用户名 → 400"""
        # Arrange: 先注册一个用户
        client.post("/register", json={
            "username": "dup_test",
            "email": "first@example.com",
            "password": "password123",
        })

        # Act: 用相同用户名再注册
        response = client.post("/register", json={
            "username": "dup_test",
            "email": "second@example.com",
            "password": "another456",
        })

        # Assert: 应返回 400 冲突
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    def test_register_duplicate_email(self, client):
        """重复邮箱 → 400"""
        client.post("/register", json={
            "username": "user_a",
            "email": "same@example.com",
            "password": "password123",
        })

        response = client.post("/register", json={
            "username": "user_b",
            "email": "same@example.com",  # 同一邮箱
            "password": "password456",
        })

        assert response.status_code == 400
        assert "邮箱" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════
# 参数化测试（5.1 §7.2）
# ═══════════════════════════════════════════════════════════

@pytest.mark.parametrize("username,password,email,expected_status,desc", [
    # ── 正常情况 ──
    ("valid_user", "valid123", "valid@example.com", 201, "正常注册"),
    # ── 用户名边界 ──
    ("ab", "valid123", "short_uname@b.com", 422, "用户名太短（2字符）"),
    ("a" * 51, "valid123", "long_uname@b.com", 422, "用户名太长（51字符）"),
    # ── 密码边界 ──
    ("test_user", "12345", "short_pwd@b.com", 422, "密码太短（5字符）"),
    # ── 邮箱格式 ──
    ("test_user", "valid123", "not-an-email", 422, "邮箱格式不合法"),
])
def test_register_validation(client, username, password, email, expected_status, desc):
    """
    参数化测试注册接口的输入校验。

    用 @pytest.mark.parametrize 一次性覆盖 6 种场景，
    避免写 6 个几乎相同的测试函数。
    """
    response = client.post("/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    assert response.status_code == expected_status, f"场景 '{desc}' 失败"


# ═══════════════════════════════════════════════════════════
# 查询测试
# ═══════════════════════════════════════════════════════════

class TestGetUsers:
    """用户查询相关测试"""

    def test_get_user_success(self, client):
        """查询存在的用户 → 200"""
        # Arrange: 先创建一个用户
        r = client.post("/register", json={
            "username": "query_test",
            "email": "query@example.com",
            "password": "testpass123",
        })
        user_id = r.json()["id"]

        # Act
        response = client.get(f"/users/{user_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["username"] == "query_test"

    def test_get_user_not_found(self, client):
        """查询不存在的用户 → 404"""
        response = client.get("/users/99999")
        assert response.status_code == 404

    def test_list_users(self, client):
        """用户列表 → 200，应包含已注册用户"""
        # Arrange: 注册两个用户
        client.post("/register", json={
            "username": "list_a", "email": "lista@x.com", "password": "pwdpwdpwd"
        })
        client.post("/register", json={
            "username": "list_b", "email": "listb@x.com", "password": "pwdpwdpwd"
        })

        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


# ═══════════════════════════════════════════════════════════
# 更新测试
# ═══════════════════════════════════════════════════════════

class TestUpdateUser:
    """用户更新相关测试"""

    def test_update_own_profile(self, client):
        """
        更新自己的信息 → 200。

        这里通过真实注册+登录来获取身份（而非覆盖依赖），
        演示"走真实认证流程"的集成测试。
        """
        # Arrange: 注册 + 登录
        client.post("/register", json={
            "username": "updateme",
            "email": "updateme@x.com",
            "password": "testpass123",
        })
        login_r = client.post("/login", json={
            "username": "updateme", "password": "testpass123"
        })
        token = login_r.json()["access_token"]

        # 从 /users 列表中找到自己的 id
        users_r = client.get("/users")
        my_id = [u for u in users_r.json() if u["username"] == "updateme"][0]["id"]

        # Act: 带 Token 更新自己
        response = client.patch(
            f"/users/{my_id}",
            json={"username": "updated_name"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["username"] == "updated_name"

    def test_update_other_user_forbidden(self, client):
        """
        更新别人的信息 → 403。

        数据所有权测试：普通用户不能改别人的信息。
        """
        # Arrange: 创建两个用户
        client.post("/register", json={
            "username": "owner", "email": "owner@x.com", "password": "testpass123"
        })
        client.post("/register", json={
            "username": "intruder", "email": "intruder@x.com", "password": "testpass123"
        })
        login_r = client.post("/login", json={
            "username": "intruder", "password": "testpass123"
        })
        token = login_r.json()["access_token"]

        # 找到 owner 的 id
        users = client.get("/users").json()
        owner_id = [u for u in users if u["username"] == "owner"][0]["id"]

        # Act: intruder 试图修改 owner
        response = client.patch(
            f"/users/{owner_id}",
            json={"username": "hacked!"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════
# 删除测试
# ═══════════════════════════════════════════════════════════

class TestDeleteUser:
    """用户删除相关测试"""

    def test_delete_own_account(self, client):
        """删除自己的账号 → 200 → 查不到"""
        # Arrange
        client.post("/register", json={
            "username": "deleteme",
            "email": "deleteme@x.com",
            "password": "testpass123",
        })
        login_r = client.post("/login", json={
            "username": "deleteme", "password": "testpass123"
        })
        token = login_r.json()["access_token"]

        users = client.get("/users").json()
        my_id = [u for u in users if u["username"] == "deleteme"][0]["id"]

        # Act: 删除自己
        response = client.delete(
            f"/users/{my_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200

        # 确认已删除
        get_response = client.get(f"/users/{my_id}")
        assert get_response.status_code == 404
