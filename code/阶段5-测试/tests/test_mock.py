"""
test_mock.py — Mock 与依赖覆盖测试（对应 5.2）

本文件演示：
  1. MagicMock：模拟同步函数
  2. AsyncMock：模拟异步函数
  3. side_effect：模拟不同的返回值（成功 / 失败 / 超时）
  4. assert_called_once：验证 Mock 确实被调用了
  5. unittest.mock.patch：临时替换模块内部的函数
  6. 模拟外部服务失败时的降级处理

运行：
  pytest tests/test_mock.py -v
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

from app.routers import posts  # fetch_weather_from_external 在此模块中
from app.main import app
from app.database import get_db


# ═══════════════════════════════════════════════════════════
# 1. MagicMock 基础（5.2 §3.1）
# ═══════════════════════════════════════════════════════════

class TestMagicMockBasics:
    """演示 MagicMock 的基本用法"""

    def test_mock_return_value(self):
        """Mock 返回固定值"""
        # 创建一个假函数
        fake_func = MagicMock()
        fake_func.return_value = {"status": "ok", "id": 123}

        # 调用——无论传什么参数，都返回固定值
        result = fake_func("anything", keyword="whatever")
        assert result == {"status": "ok", "id": 123}

        # 验证被调用过一次
        fake_func.assert_called_once()

    def test_mock_side_effect_sequence(self):
        """Mock 每次返回不同值"""
        fake_func = MagicMock()
        fake_func.side_effect = [
            {"status": "ok"},        # 第 1 次调用
            {"status": "ok"},        # 第 2 次调用
            Exception("服务超时"),    # 第 3 次调用 → 抛异常
        ]

        assert fake_func() == {"status": "ok"}
        assert fake_func() == {"status": "ok"}
        with pytest.raises(Exception) as exc_info:
            fake_func()
        assert "服务超时" in str(exc_info.value)

    def test_mock_side_effect_dynamic(self):
        """Mock 根据输入动态返回"""
        fake_func = MagicMock()

        def dynamic_response(arg1, **kwargs):
            if arg1 == "valid":
                return {"status": "ok"}
            else:
                raise ValueError("无效参数")

        fake_func.side_effect = dynamic_response

        assert fake_func("valid") == {"status": "ok"}
        with pytest.raises(ValueError):
            fake_func("invalid")


# ═══════════════════════════════════════════════════════════
# 2. Mock 外部服务调用（5.2 §3 + §6）
# ═══════════════════════════════════════════════════════════

class TestMockExternalService:
    """
    Mock 外部天气服务。

    真实场景中 fetch_weather_from_external 会调第三方 API，
    测试时通过覆盖依赖，返回固定值。
    """

    def test_weather_success(self, client):
        """
        Mock 外部天气服务返回成功 → 200。

        用 MagicMock 替换 main.fetch_weather_from_external，
        返回固定的天气数据，不真的调外部 API。
        """
        # 创建 Mock
        mock_weather = AsyncMock()  # async def 用 AsyncMock
        mock_weather.return_value = {
            "city": "北京",
            "temperature": 25,
            "condition": "晴",
            "source": "mocked",  # ← 标记为 Mock 数据
        }

        # fetch_weather_from_external 在 routers/posts.py 中直接 await 调用，
        # 不是依赖注入，需要用 unittest.mock.patch 来替换它。
        with patch("app.routers.posts.fetch_weather_from_external", new_callable=AsyncMock) as mock_fn:
            mock_fn.return_value = {
                "city": "北京",
                "temperature": 25,
                "condition": "晴",
                "source": "mocked",
            }

            response = client.get("/weather?city=北京")

            assert response.status_code == 200
            data = response.json()
            assert data["temperature"] == 25
            assert data["source"] == "mocked"
            mock_fn.assert_called_once()  # 验证确实被调用了

    def test_weather_timeout(self, client):
        """
        模拟外部天气服务超时 → 500。

        side_effect = TimeoutError 模拟网络超时。
        验证接口在外部服务不可用时返回友好错误。
        """
        with patch("app.routers.posts.fetch_weather_from_external", new_callable=AsyncMock) as mock_fn:
            # 模拟超时
            mock_fn.side_effect = TimeoutError("外部服务连接超时")

            response = client.get("/weather?city=上海")

            assert response.status_code == 500
            assert "暂不可用" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════
# 3. Mock 短信服务示例（5.2 §6 完整流程）
# ═══════════════════════════════════════════════════════════

# 为了演示，我们在运行时注入一个假的发送通知函数
def fake_send_notification(user_email: str, message: str) -> dict:
    """假的发送通知函数（用于演示）"""
    return {"sent": True, "to": user_email}


class TestMockNotification:
    """演示用依赖覆盖 Mock 通知服务"""

    def test_mock_notification_service(self, client):
        """
        用依赖覆盖替换通知服务。

        演示概念：如果 main.py 中有发送通知的依赖，
        可以通过 app.dependency_overrides 替换它。
        """
        # 假设有一个通知函数
        mock_notify = MagicMock()
        mock_notify.return_value = {"sent": True, "message_id": "mock-001"}

        # 如果 main.py 中有对应的依赖，这里可以覆盖
        # app.dependency_overrides[...] = mock_notify

        # 先验证 MagicMock 行为
        result = mock_notify("user@example.com", "欢迎注册！")
        assert result == {"sent": True, "message_id": "mock-001"}
        mock_notify.assert_called_once_with("user@example.com", "欢迎注册！")


# ═══════════════════════════════════════════════════════════
# 4. 完整业务流程 Mock 测试（5.2 §6）
# ═══════════════════════════════════════════════════════════

class TestFullFlowWithMock:
    """
    完整的业务流程测试：注册 → Mock 外部服务 → 登录 → 访问。

    演示如何在一个测试中组合：
      - TestClient 发请求
      - patch 模拟外部函数
      - 断言整个流程的数据一致性
    """

    def test_full_registration_flow(self, client):
        """
        完整注册流程，Mock 外部服务。

        场景：用户注册时，系统"发送"欢迎通知。
        实际上通知函数被 Mock 了，不会真的发送。
        """
        # Mock 外部通知服务
        mock_notify = MagicMock()
        mock_notify.return_value = {"sent": True}

        # 注册用户
        response = client.post("/register", json={
            "username": "flowtest",
            "email": "flowtest@example.com",
            "password": "testpass123",
        })
        assert response.status_code == 201
        user_id = response.json()["id"]

        # 登录
        login_response = client.post("/login", json={
            "username": "flowtest",
            "password": "testpass123",
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 验证用户数据一致性
        user_response = client.get(f"/users/{user_id}")
        assert user_response.status_code == 200
        assert user_response.json()["username"] == "flowtest"
        assert user_response.json()["email"] == "flowtest@example.com"

        # 确认 Mock 的行为符合预期（即使没真的在 main.py 中使用它）
        # 在实际项目中，你会在注册端点中调用 send_notification 依赖，
        # 然后这里：mock_notify.assert_called_once()


# ═══════════════════════════════════════════════════════════
# 5. sync vs async Mock 对比（5.2 §3.3）
# ═══════════════════════════════════════════════════════════

class TestSyncAsyncMock:
    """演示同步和异步 Mock 的区别"""

    def test_magicmock_for_sync(self):
        """同步函数用 MagicMock"""
        sync_mock = MagicMock(return_value="sync_result")
        result = sync_mock()
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_asyncmock_for_async(self):
        """异步函数用 AsyncMock"""
        async_mock = AsyncMock(return_value="async_result")
        result = await async_mock()
        assert result == "async_result"
