"""
6.1 后台任务 — 可运行 Demo

运行方式:
    cd code/阶段6-高级特性/6.1-后台任务
    pip install fastapi uvicorn[standard]
    uvicorn main:app --reload
    浏览器打开 http://127.0.0.1:8000/docs

本 Demo 涵盖:
  1. BackgroundTasks 基本用法（注册后发"欢迎邮件"）
  2. 多个后台任务（发邮件 + 写日志）
  3. 对比：有/无后台任务的响应时间差异
  4. 模拟耗时任务（文件处理）
"""

import time
import os
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(
    title="6.1 后台任务 Demo",
    description="学习 BackgroundTasks 的完整示例",
    version="1.0.0",
)

# ═══════════════════════════════════════════════════════════
# 模拟耗时操作（实际项目中这些会调外部服务）
# ═══════════════════════════════════════════════════════════

def send_welcome_email(email: str, username: str):
    """
    模拟发送欢迎邮件 —— 实际耗时约 2-3 秒。

    注意：这是一个同步 def 函数，BackgroundTasks 会在
    响应返回后在线程池中执行它，不会阻塞事件循环。
    """
    print(f"\n📧 [后台] 开始发送欢迎邮件给 {email}...")
    time.sleep(2)  # 模拟 SMTP 发送耗时
    print(f"✅ [后台] 欢迎邮件已发送给 {username} ({email})")


def write_registration_log(user_id: int, username: str):
    """
    模拟写注册日志到文件 —— 实际耗时约 0.1 秒。

    每个后台任务独立执行，一个失败不影响另一个。
    """
    print(f"\n📝 [后台] 写入注册日志...")
    time.sleep(0.5)  # 模拟 I/O 耗时
    log_line = f"[{datetime.now().isoformat()}] 新用户注册: id={user_id}, username={username}\n"
    # 实际项目中写数据库或日志文件
    print(f"✅ [后台] 日志已记录: {log_line.strip()}")


def generate_thumbnail(image_path: str):
    """
    模拟生成缩略图 —— 实际耗时约 3-5 秒。

    图片处理是 BackgroundTasks 的典型场景：
    上传完成后立刻返回"上传成功"，缩略图后台慢慢生成。
    """
    print(f"\n🖼️  [后台] 正在生成缩略图: {image_path}...")
    time.sleep(3)
    print(f"✅ [后台] 缩略图已生成: {image_path.replace('.', '_thumb.')}")


# ═══════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════

# 模拟的内存数据库
fake_db: list[dict] = []
user_id_counter = 1


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["zhangsan"])
    email: EmailStr = Field(examples=["zhang@example.com"])


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    registered_at: str


# ═══════════════════════════════════════════════════════════
# 端点
# ═══════════════════════════════════════════════════════════

@app.get("/")
def root():
    """
    首页 → 快速测试后台任务。

    访问这个页面，你会立刻得到响应，
    但后台任务会在终端输出中打印出来（观察控制台）。
    """
    return {
        "message": "后台任务 Demo",
        "endpoints": {
            "POST /register": "注册用户（触发后台任务：发邮件 + 写日志）",
            "POST /register-without-bg": "注册用户（无后台任务——感受响应时间差异）",
            "POST /upload-image": "模拟上传图片（触发后台生成缩略图）",
            "GET /users": "查看所有已注册用户",
        }
    }


@app.post("/register", response_model=UserResponse)
def register(data: UserCreate, background_tasks: BackgroundTasks):
    """
    用户注册 —— 使用后台任务。

    流程:
      1. 创建用户（瞬间完成）
      2. 把"发欢迎邮件"和"写日志"丢给后台
      3. 立刻返回响应给用户

    在 Swagger UI 中测试后，观察终端输出：
      - 你会先看到 HTTP 响应
      - 2-3 秒后才看到"邮件已发送"
    """
    global user_id_counter

    # 检查重复用户名
    for u in fake_db:
        if u["username"] == data.username:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="用户名已存在")

    # 1. 创建用户
    user = {
        "id": user_id_counter,
        "username": data.username,
        "email": data.email,
        "registered_at": datetime.now().isoformat(),
    }
    fake_db.append(user)
    user_id_counter += 1

    # 2. 把耗时操作丢给后台
    background_tasks.add_task(
        send_welcome_email,
        email=user["email"],
        username=user["username"],
    )
    background_tasks.add_task(
        write_registration_log,
        user_id=user["id"],
        username=user["username"],
    )

    # 3. 立刻返回 —— 用户不用等邮件发送
    print(f"⚡ [主请求] 用户 {user['username']} 注册完成，响应已返回")
    return UserResponse(**user)


@app.post("/register-without-bg", response_model=UserResponse)
def register_without_bg(data: UserCreate):
    """
    用户注册 —— 不使用后台任务（对比用）。

    注意：这个接口会阻塞 2-3 秒才返回响应！
    在 Swagger UI 中试试，感受时间差。
    """
    global user_id_counter

    for u in fake_db:
        if u["username"] == data.username:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="用户名已存在")

    user = {
        "id": user_id_counter,
        "username": data.username,
        "email": data.email,
        "registered_at": datetime.now().isoformat(),
    }
    fake_db.append(user)
    user_id_counter += 1

    # 同步执行——用户要等到这俩都执行完才能拿到响应！
    send_welcome_email(user["email"], user["username"])
    write_registration_log(user["id"], user["username"])

    return UserResponse(**user)


@app.get("/users", response_model=list[UserResponse])
def list_users():
    """查看所有已注册用户"""
    return [UserResponse(**u) for u in fake_db]


@app.post("/upload-image")
def upload_image(
    filename: str = "photo.jpg",
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    模拟上传图片 → 后台生成缩略图。

    响应立刻返回"上传成功"，缩略图在后台慢慢生成。
    观察终端输出：先看到 HTTP 响应日志，3 秒后才看到"缩略图已生成"。
    """
    # 模拟保存文件
    print(f"💾 [主请求] 文件 {filename} 已保存")

    # 后台生成缩略图
    background_tasks.add_task(generate_thumbnail, f"uploads/{filename}")

    return {
        "message": f"文件 {filename} 上传成功！",
        "hint": "缩略图正在后台生成中，观察终端输出...",
    }


@app.get("/learn")
def learn_background_tasks():
    """
    学习总结 —— BackgroundTasks 的适用场景和局限性。
    """
    return {
        "适用场景": [
            "发送邮件（注册欢迎、密码重置、通知）",
            "写审计日志（不拖慢业务响应）",
            "生成缩略图（上传后异步处理）",
            "推送 Web 通知",
            "更新统计计数器",
        ],
        "不适用场景": [
            "支付回调（需要重试 + 状态追踪 → Celery）",
            "批量导出报表（需要进度反馈 → Celery）",
            "定时任务（需要调度 → Celery Beat）",
            "高并发大量任务（需要分布式队列 → Celery + Redis）",
        ],
        "关键对比": {
            "BackgroundTasks": "无重试、无持久化、零配置、适合轻量任务",
            "Celery": "有重试、持久化到 Redis/RabbitMQ、多 Worker 并行、功能强大",
        },
    }


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  6.1 后台任务 Demo")
    print("  http://127.0.0.1:8000/docs")
    print("=" * 60)
    print()
    print("💡 测试提示:")
    print("  1. 在 Swagger 中 POST /register，观察终端输出")
    print("  2. 对比 POST /register-without-bg，感受响应时间差异")
    print("  3. 看 GET /learn 了解 BackgroundTasks 的全貌")
    print()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
