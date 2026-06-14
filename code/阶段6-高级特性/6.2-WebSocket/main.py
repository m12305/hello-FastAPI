"""
6.2 WebSocket — 可运行 Demo：简易在线聊天室

运行方式:
    cd code/阶段6-高级特性/6.2-WebSocket
    pip install fastapi uvicorn[standard]
    uvicorn main:app --reload

访问:
    浏览器打开 http://127.0.0.1:8000/chat  → 聊天室页面
    浏览器打开 http://127.0.0.1:8000/docs  → Swagger UI

本 Demo 涵盖:
  1. WebSocket 连接建立/断开
  2. 广播消息（所有人可见）
  3. 私聊消息（@某用户）
  4. 系统通知（加入/离开）
  5. 在线用户列表
  6. ConnectionManager 封装模式
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import dict
import asyncio

app = FastAPI(
    title="6.2 WebSocket Demo — 简易聊天室",
    description="学习 WebSocket 双向通信的完整示例",
    version="1.0.0",
)


# ═══════════════════════════════════════════════════════════
# ConnectionManager：管理所有 WebSocket 连接
# ═══════════════════════════════════════════════════════════

class ConnectionManager:
    """
    WebSocket 连接管理器。

    职责:
      1. 接受新连接
      2. 维护 连接→用户名 映射
      3. 广播消息
      4. 发送私聊消息
      5. 维护在线用户列表
    """

    def __init__(self):
        # {websocket: "username"}
        self.active_connections: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[websocket] = username
        # 通知所有人
        await self.broadcast(f"🎉 {username} 加入了聊天室", system=True)
        await self._notify_user_list_changed()

    def disconnect(self, websocket: WebSocket) -> str:
        """移除连接，返回离开的用户名"""
        username = self.active_connections.pop(websocket, "未知用户")
        return username

    async def broadcast(self, message: str, system: bool = False):
        """
        向所有在线用户广播消息。

        system=True 表示系统通知（格式不同）。
        """
        if system:
            formatted = f"📢 系统: {message}"
        else:
            formatted = message

        # 向每个连接发送
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(formatted)
            except Exception:
                disconnected.append(ws)

        # 清理断开的连接
        for ws in disconnected:
            self.disconnect(ws)

        if disconnected:
            await self._notify_user_list_changed()

    async def send_personal(self, message: str, websocket: WebSocket):
        """发送私密消息给指定连接"""
        try:
            await websocket.send_text(message)
        except Exception:
            pass

    async def send_to_user(self, message: str, target_username: str, sender: str) -> bool:
        """
        发送私聊消息给指定用户。

        返回 True 表示发送成功，False 表示目标用户不在线。
        """
        for ws, name in self.active_connections.items():
            if name == target_username:
                await ws.send_text(f"🔒 {sender} 悄悄对你说: {message}")
                return True
        return False

    async def _notify_user_list_changed(self):
        """通知所有客户端：在线用户列表变了"""
        user_list = list(self.active_connections.values())
        for ws in self.active_connections:
            try:
                await ws.send_json({"type": "user_list", "users": user_list})
            except Exception:
                pass

    def get_online_users(self) -> list[str]:
        """获取在线用户列表"""
        return list(self.active_connections.values())


manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════
# 聊天室 WebSocket 端点
# ═══════════════════════════════════════════════════════════

@app.websocket("/ws/chat/{username}")
async def chat_endpoint(websocket: WebSocket, username: str):
    """
    WebSocket 聊天端点。

    连接后:
      1. 广播 "{username} 加入了聊天室"
      2. 接收消息:
         - "消息内容"       → 广播给所有人
         - "@用户名 消息"   → 私聊给指定用户（注意空格！）
         - "/users"         → 查看在线用户
      3. 断开时广播 "{username} 离开了聊天室"
    """
    await manager.connect(websocket, username)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()

            # ── 命令处理 ──
            if data == "/users":
                users = manager.get_online_users()
                await manager.send_personal(
                    f"📋 在线用户 ({len(users)}人): {', '.join(users)}",
                    websocket,
                )
                continue

            # ── 私聊: @用户名 消息内容 ──
            if data.startswith("@"):
                parts = data[1:].split(" ", 1)  # 去掉 @，用第一个空格分割
                if len(parts) >= 2:
                    target, message = parts[0], parts[1]
                    sent = await manager.send_to_user(message, target, username)
                    if not sent:
                        await manager.send_personal(
                            f"⚠️ 用户 '{target}' 不在线",
                            websocket,
                        )
                    else:
                        # 也给自己回显
                        await manager.send_personal(
                            f"🔒 你对 {target} 悄悄说: {message}",
                            websocket,
                        )
                else:
                    await manager.send_personal(
                        "⚠️ 用法: @用户名 消息内容（注意 @ 后面有一个空格）",
                        websocket,
                    )
                continue

            # ── 普通消息: 广播 ──
            await manager.broadcast(f"💬 {username}: {data}")

    except WebSocketDisconnect:
        # 用户关闭页面或断开连接
        manager.disconnect(websocket)
        await manager.broadcast(f"👋 {username} 离开了聊天室", system=True)


# ═══════════════════════════════════════════════════════════
# 聊天室 HTML 页面
# ═══════════════════════════════════════════════════════════

CHAT_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket 聊天室</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', 'PingFang SC', sans-serif;
            max-width: 700px;
            margin: 30px auto;
            padding: 20px;
            background: #f5f7fa;
        }
        h2 { color: #1a1a2e; margin-bottom: 15px; }
        .status { color: #666; font-size: 14px; margin-bottom: 10px; }
        .status .dot { display: inline-block; width: 8px; height: 8px;
            background: #4caf50; border-radius: 50%; margin-right: 5px; }

        #messages {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #fff;
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            margin-bottom: 12px;
        }
        .msg { padding: 6px 0; border-bottom: 1px solid #f0f0f0;
            font-size: 14px; line-height: 1.5; word-break: break-all; }

        .input-row { display: flex; gap: 8px; }
        #input { flex: 1; padding: 10px 14px; border: 1px solid #ddd;
            border-radius: 8px; font-size: 14px; outline: none; }
        #input:focus { border-color: #4a90d9; box-shadow: 0 0 0 2px rgba(74,144,217,0.2); }
        button { padding: 10px 20px; background: #4a90d9; color: #fff;
            border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
        button:hover { background: #357abd; }
        .hint { color: #999; font-size: 12px; margin-top: 8px; }
        .system-msg { color: #888; font-style: italic; }
    </style>
</head>
<body>
    <h2>💬 WebSocket 聊天室</h2>
    <div class="status">
        <span class="dot" id="status-dot"></span>
        <span id="status-text">连接中...</span>
        <span style="margin-left: 15px; color: #888;">在线: <span id="online-count">0</span> 人</span>
    </div>

    <div id="messages"></div>

    <div class="input-row">
        <input id="input" type="text" placeholder="输入消息... (@用户名 内容 = 私聊, /users = 在线列表)" autofocus>
        <button onclick="send()">发送</button>
    </div>
    <div class="hint">💡 @用户名 消息内容 → 私聊 | /users → 查看在线用户</div>

    <script>
        // 随机用户名（每次刷新都不一样——实际项目用登录系统）
        const username = "用户" + Math.floor(Math.random() * 1000);
        let ws = null;

        function connect() {
            ws = new WebSocket(`ws://${location.host}/ws/chat/${username}`);

            ws.onopen = () => {
                document.getElementById("status-text").textContent = `已连接 (${username})`;
                document.getElementById("status-dot").style.background = "#4caf50";
            };

            ws.onmessage = (event) => {
                const data = event.data;
                try {
                    // 尝试解析 JSON（用户列表更新）
                    const json = JSON.parse(data);
                    if (json.type === "user_list") {
                        document.getElementById("online-count").textContent = json.users.length;
                        return;
                    }
                } catch (e) {
                    // 不是 JSON，是普通消息
                }

                const messages = document.getElementById("messages");
                const isSystem = data.startsWith("📢");
                messages.innerHTML += `<div class="msg ${isSystem ? 'system-msg' : ''}">${data}</div>`;
                messages.scrollTop = messages.scrollHeight;
            };

            ws.onclose = () => {
                document.getElementById("status-text").textContent = "已断开，3秒后重连...";
                document.getElementById("status-dot").style.background = "#f44336";
                setTimeout(connect, 3000);
            };

            ws.onerror = () => {
                document.getElementById("status-text").textContent = "连接错误";
                document.getElementById("status-dot").style.background = "#f44336";
            };
        }

        function send() {
            const input = document.getElementById("input");
            const text = input.value.trim();
            if (!text) return;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(text);
                input.value = "";
            }
        }

        document.getElementById("input").addEventListener("keydown", (e) => {
            if (e.key === "Enter") send();
        });

        // 启动连接
        connect();
    </script>
</body>
</html>
"""


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """
    聊天室 HTML 页面。

    打开这个页面 → 自动建立 WebSocket 连接 → 开始聊天！
    建议同时打开 2-3 个浏览器标签页，用不同用户名测试广播和私聊。
    """
    return CHAT_HTML


# ═══════════════════════════════════════════════════════════
# 辅助 REST 端点
# ═══════════════════════════════════════════════════════════

@app.get("/online-users")
def online_users():
    """查看在线用户列表（REST 接口）"""
    users = manager.get_online_users()
    return {"count": len(users), "users": users}


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  6.2 WebSocket Demo — 简易聊天室")
    print("  聊天室: http://127.0.0.1:8000/chat")
    print("  API文档: http://127.0.0.1:8000/docs")
    print("=" * 60)
    print()
    print("💡 测试提示:")
    print("  1. 打开 2-3 个浏览器标签页访问 /chat")
    print("  2. 发消息 → 所有标签页都能看到（广播）")
    print("  3. 输入 @用户名 消息 → 只有那个人能看到（私聊）")
    print("  4. 输入 /users → 查看在线用户列表")
    print("  5. 关闭一个标签页 → 其他人看到离开通知")
    print()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
