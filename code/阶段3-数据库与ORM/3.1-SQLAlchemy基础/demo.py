"""
3.1 SQLAlchemy 基础 — 可运行 Demo

运行方式:
    cd code/阶段3-数据库与ORM/3.1-SQLAlchemy基础
    python demo.py

本脚本涵盖:
  1. 创建引擎（SQLite）
  2. 定义基类与模型（User + Post + 一对多关系）
  3. 创建表
  4. CRUD 操作（增删改查）
  5. 关系查询（正向 + 反向）
  6. 事务管理（commit / rollback）
  7. 筛选、排序、分页

运行后会在当前目录生成 demo.db 文件。
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    String,
    Integer,
    DateTime,
    ForeignKey,
    select,
    func,
    update,
    delete,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    Session,
    sessionmaker,
    relationship,
)


# ═══════════════════════════════════════════════════════════
# 1. 引擎 & 会话工厂
# ═══════════════════════════════════════════════════════════
engine = create_engine("sqlite:///./demo.db", echo=False)
#                            ↑
#                            设为 True 可查看所有生成的 SQL

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,    # 手动控制 flush 时机
    autocommit=False,   # 手动控制事务提交
)


# ═══════════════════════════════════════════════════════════
# 2. 基类
# ═══════════════════════════════════════════════════════════
class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


# ═══════════════════════════════════════════════════════════
# 3. 模型定义
# ═══════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    age: Mapped[int | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # 反向关系：user.posts 可以拿到该用户的所有文章
    posts: Mapped[list["Post"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",  # 删除用户时级联删除所有文章
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String(5000), default="")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # 正向关系：post.author 可以拿到这篇文章的作者
    author: Mapped["User"] = relationship(back_populates="posts")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title[:30]}...', user_id={self.user_id})>"


# ═══════════════════════════════════════════════════════════
# 4. 建表
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("📦 创建数据库表...")
Base.metadata.create_all(bind=engine)
print("✅ 表已创建（如不存在）")
# 注意：create_all 不会修改已存在的表，实际项目用 Alembic


# ═══════════════════════════════════════════════════════════
# 5. CRUD 全流程演示
# ═══════════════════════════════════════════════════════════

def demo_create(session: Session):
    """增加 — Create"""
    print("\n" + "─" * 60)
    print("📝 CREATE — 创建数据")

    # 创建单个用户
    user = User(username="张三", email="zhang@example.com", age=25)
    session.add(user)
    session.commit()
    session.refresh(user)  # 刷新以获取数据库生成的 id 和 server_default 值
    print(f"   ✅ 创建用户: {user}")

    # 批量创建
    users = [
        User(username="李四", email="li@example.com", age=30),
        User(username="王五", email="wang@example.com", age=28),
        User(username="赵六", email="zhao@example.com", age=35),
    ]
    session.add_all(users)
    session.commit()
    for u in users:
        session.refresh(u)
        print(f"   ✅ 创建用户: {u}")

    # 给张三创建文章
    posts = [
        Post(title="FastAPI 入门指南", content="FastAPI 是一个现代 Web 框架...", user_id=user.id),
        Post(title="SQLAlchemy 2.0 笔记", content="使用 Mapped 注解定义列...", user_id=user.id),
        Post(title="Python 异步编程", content="async/await 的工作原理...", user_id=user.id),
    ]
    session.add_all(posts)
    session.commit()
    for p in posts:
        session.refresh(p)
        print(f"   ✅ 创建文章: {p}")

    return user, users, posts


def demo_read(session: Session, user_id: int):
    """查 — Read"""
    print("\n" + "─" * 60)
    print("🔍 READ — 查询数据")

    # 按主键查（最高效）
    user = session.get(User, user_id)
    print(f"   按主键查询 (session.get): {user}")

    # 按条件查单个
    stmt = select(User).where(User.email == "li@example.com")
    found = session.scalars(stmt).first()
    print(f"   按邮箱查询 (.first()):    {found}")

    # 查多个 — 筛选 + 排序
    stmt = (
        select(User)
        .where(User.age >= 25, User.is_active == True)
        .order_by(User.age.desc())
    )
    active_users = session.scalars(stmt).all()
    print(f"   筛选 (age>=25, 活跃):    {len(active_users)} 人")
    for u in active_users:
        print(f"      - {u.username}, {u.age}岁")

    # 分页查询
    stmt = select(User).offset(0).limit(2)
    page1 = session.scalars(stmt).all()
    print(f"   分页 (offset=0, limit=2): {[u.username for u in page1]}")


def demo_update(session: Session, user_id: int):
    """改 — Update"""
    print("\n" + "─" * 60)
    print("✏️  UPDATE — 更新数据")

    # 方式 1：查出实例 → 修改属性 → commit
    user = session.get(User, user_id)
    old_age = user.age
    user.age = 26
    user.email = "zhangsan_new@example.com"
    session.commit()
    session.refresh(user)
    print(f"   方式1 (修改属性): {old_age}岁 → {user.age}岁, 新邮箱: {user.email}")

    # 方式 2：批量更新（不用先查出实例）
    stmt = (
        update(User)
        .where(User.age < 30)
        .values(is_active=False)
    )
    result = session.execute(stmt)
    session.commit()
    print(f"   方式2 (批量更新): {result.rowcount} 行被标记为非活跃")


def demo_delete(session: Session, user_id: int):
    """删 — Delete"""
    print("\n" + "─" * 60)
    print("🗑️  DELETE — 删除数据")

    # 先看有几个用户
    count_before = session.scalar(select(func.count()).select_from(User))
    print(f"   删除前用户数: {count_before}")

    # 方式 1：查出实例 → delete → commit
    user = session.get(User, user_id)
    if user:
        session.delete(user)
        session.commit()
        print(f"   方式1 (查出再删): 已删除 {user.username}")

    # 方式 2：批量删除
    stmt = delete(User).where(User.is_active == False)
    result = session.execute(stmt)
    session.commit()
    print(f"   方式2 (批量删除非活跃): {result.rowcount} 行已删除")

    count_after = session.scalar(select(func.count()).select_from(User))
    print(f"   删除后用户数: {count_after}")


def demo_relationships(session: Session):
    """关系查询 — Relationship"""
    print("\n" + "─" * 60)
    print("🔗 关系查询 — Relationship")

    # 查一个还有文章的用户
    stmt = (
        select(User)
        .where(User.posts.any())  # 至少有 1 篇文章
        .order_by(User.id)
        .limit(1)
    )
    user = session.scalars(stmt).first()

    if not user:
        print("   ⚠️ 没找到有文章的用户，跳过关系演示")
        return

    # 正向：从 Post 找到作者
    post = user.posts[0] if user.posts else None
    if post:
        print(f"   正向关系 (post.author): {post.title[:25]}... → 作者 {post.author.username}")

    # 反向：从 User 找到所有文章
    print(f"   反向关系 (user.posts): {user.username} 有 {len(user.posts)} 篇文章")
    for p in user.posts:
        print(f"      - [{p.id}] {p.title[:40]}")


def demo_transaction(session: Session):
    """事务管理演示"""
    print("\n" + "─" * 60)
    print("🔄 事务管理")

    # 正常提交
    user = User(username="事务测试", email="tx@example.com", age=20)
    session.add(user)
    session.commit()
    print(f"   ✅ 正常提交: {user.username}")

    # 模拟出错回滚
    try:
        user2 = User(username="回滚测试", email="rollback@example.com", age=20)
        session.add(user2)
        # 故意制造错误（比如违反唯一约束）
        user3 = User(username="回滚测试", email="rollback@example.com", age=20)  # 相同 username
        session.add(user3)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"   ↩️  回滚！原因: {type(e).__name__}")

    # 验证回滚成功——"回滚测试" 不应该存在
    stmt = select(User).where(User.username == "回滚测试")
    exists = session.scalars(stmt).first()
    print(f"   ✅ 验证回滚: 冲突数据{'不存在' if not exists else '存在（异常！）'}")


# ═══════════════════════════════════════════════════════════
# 6. 主流程
# ═══════════════════════════════════════════════════════════

def main():
    print("\n" + "█" * 60)
    print("█  SQLAlchemy 2.0 基础演示")
    print("█" * 60)

    session = SessionLocal()

    try:
        # 先清理上次运行的数据（保持演示可重复）
        print("\n🧹 清理旧数据...")
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.commit()
        print("✅ 旧数据已清理")

        # CRUD 演示
        user, users, posts = demo_create(session)
        demo_read(session, user.id)
        demo_relationships(session)
        demo_update(session, users[0].id)   # 更新李四
        demo_transaction(session)
        demo_delete(session, users[1].id)   # 删除王五

        # ─── 最终统计 ───
        print("\n" + "=" * 60)
        print("📊 最终数据统计")
        user_count = session.scalar(select(func.count()).select_from(User))
        post_count = session.scalar(select(func.count()).select_from(Post))
        print(f"   用户: {user_count} 人")
        print(f"   文章: {post_count} 篇")
        remaining = session.scalars(select(User).order_by(User.id)).all()
        for u in remaining:
            print(f"   - {u.username} ({u.email}), {u.age}岁, 活跃={u.is_active}")

    except Exception as e:
        session.rollback()
        print(f"\n❌ 出错: {e}")
        raise
    finally:
        session.close()
        print("\n🔒 Session 已关闭")

    print("\n" + "█" * 60)
    print("█  演示结束！数据库文件: demo.db")
    print("█" * 60)


if __name__ == "__main__":
    main()
