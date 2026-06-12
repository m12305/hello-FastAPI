"""
3.3 数据库迁移概念演示 — 可运行 Demo

运行方式:
    cd code/阶段3-数据库与ORM/3.3-Alembic数据库迁移
    python demo_migration.py

本脚本用一个轻量的"迷你迁移引擎"模拟 Alembic 的核心概念：
  1. 版本号链（revision chain）
  2. upgrade() / downgrade()
  3. 迁移历史追踪
  4. 完整工作流：创建 → 迁移 → 回滚

运行完后，参考本目录下的 alembic_setup_guide.md 在真实项目中配置 Alembic。
"""

import sqlite3
import os
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# 迷你迁移引擎（模拟 Alembic 的核心概念）
# ═══════════════════════════════════════════════════════════

class MiniMigration:
    """模拟一次数据库迁移"""

    def __init__(self, revision: str, down_revision: str, description: str):
        self.revision = revision       # 当前版本号
        self.down_revision = down_revision  # 上一个版本号
        self.description = description

    def upgrade(self, conn):
        """升级到当前版本"""
        raise NotImplementedError

    def downgrade(self, conn):
        """回滚到上一版本"""
        raise NotImplementedError


class MigrationEngine:
    """
    迷你迁移引擎 — 核心概念同 Alembic

    Alembic 等价物:
      - self.migrations  → alembic/versions/ 目录
      - self._ensure_table() → alembic_version 表
      - self.upgrade()   → alembic upgrade head
      - self.downgrade() → alembic downgrade -1
      - self.current()   → alembic current
      - self.history()   → alembic history
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations: dict[str, MiniMigration] = {}
        self.head: str | None = None  # 最新版本号

    def register(self, migration: MiniMigration):
        """注册一个迁移版本"""
        self.migrations[migration.revision] = migration
        self.head = migration.revision

    def _ensure_table(self, conn):
        """确保迁移历史表存在"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migration_version (
                version_num TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

    def _get_current_version(self, conn) -> str | None:
        """获取当前数据库的版本号"""
        self._ensure_table(conn)
        row = conn.execute("SELECT version_num FROM _migration_version").fetchone()
        return row[0] if row else None

    def upgrade(self, target: str = "head"):
        """升级到目标版本"""
        conn = sqlite3.connect(self.db_path)

        current = self._get_current_version(conn)
        target_rev = self.head if target == "head" else target

        if current == target_rev:
            print(f"  ✅ 已是最新版本 ({current})")
            conn.close()
            return

        # 构建升级链（从 current → target）
        chain = []
        rev = target_rev
        while rev and rev != current:
            if rev not in self.migrations:
                print(f"  ❌ 版本 {rev} 不存在")
                conn.close()
                return
            chain.insert(0, rev)
            rev = self.migrations[rev].down_revision

        if rev != current:
            print(f"  ❌ 版本链不连续：{current} → {target_rev}")
            conn.close()
            return

        # 依次执行升级
        for rev in chain:
            migration = self.migrations[rev]
            print(f"  ⬆  upgrading {migration.down_revision} → {rev}: {migration.description}")
            migration.upgrade(conn)
            conn.execute(
                "INSERT OR REPLACE INTO _migration_version (version_num, applied_at) VALUES (?, ?)",
                (rev, datetime.now().isoformat()),
            )
            conn.commit()

        print(f"  ✅ 升级完成: {self._get_current_version(conn)}")
        conn.close()

    def downgrade(self, steps: int = 1):
        """回滚 N 步"""
        conn = sqlite3.connect(self.db_path)

        current = self._get_current_version(conn)
        if not current:
            print("  ⚠️ 没有已应用的迁移")
            conn.close()
            return

        for _ in range(steps):
            if current not in self.migrations:
                print(f"  ❌ 找不到版本 {current} 的迁移定义")
                break

            migration = self.migrations[current]
            print(f"  ⬇  downgrading {current} → {migration.down_revision}: {migration.description}")
            migration.downgrade(conn)
            conn.execute("DELETE FROM _migration_version WHERE version_num = ?", (current,))
            conn.commit()
            current = migration.down_revision
            if not current:
                break

        final = self._get_current_version(conn)
        print(f"  ✅ 回滚完成: {final or '(初始状态)'}")
        conn.close()

    def current(self):
        """查看当前版本"""
        conn = sqlite3.connect(self.db_path)
        version = self._get_current_version(conn)
        if version:
            desc = self.migrations.get(version, MiniMigration(version, "?", "未知")).description
            print(f"  当前版本: {version} ({desc})")
        else:
            print(f"  当前版本: (无 — 数据库处于初始状态)")
        conn.close()

    def history(self):
        """查看所有版本历史"""
        print(f"\n  迁移版本链:")
        chain = []
        rev = self.head
        while rev:
            m = self.migrations.get(rev)
            if m:
                chain.append(f"  {rev}  ← {m.description}")
                rev = m.down_revision
            else:
                break
        if not chain:
            print("    (空)")
        for item in reversed(chain):
            print(item)


# ═══════════════════════════════════════════════════════════
# 定义两次数据库结构变更
# ═══════════════════════════════════════════════════════════

class Migration001_Initial(MiniMigration):
    """初始建表：创建 users 表"""

    def __init__(self):
        super().__init__(
            revision="001_initial",
            down_revision=None,
            description="创建 users 表（id, username, email）",
        )

    def upgrade(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # 插入初始数据
        conn.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("admin", "admin@example.com"),
        )

    def downgrade(self, conn):
        conn.execute("DROP TABLE IF EXISTS users")


class Migration002_AddBio(MiniMigration):
    """第一次变更：给 users 表加 bio 和 avatar_url 字段"""

    def __init__(self):
        super().__init__(
            revision="002_add_bio",
            down_revision="001_initial",
            description="给 users 表新增 bio（简介）和 avatar_url（头像）字段",
        )

    def upgrade(self, conn):
        conn.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
        conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT ''")
        # 给已有用户设置默认简介
        conn.execute(
            "UPDATE users SET bio = '这个用户很懒，什么都没写...' WHERE bio = ''"
        )

    def downgrade(self, conn):
        # SQLite 不支持 DROP COLUMN（旧版本），所以用重建表的方式
        conn.execute("""
            CREATE TABLE users_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            INSERT INTO users_temp (id, username, email, is_active, created_at)
            SELECT id, username, email, is_active, created_at FROM users
        """)
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_temp RENAME TO users")


# ═══════════════════════════════════════════════════════════
# 演示流程
# ═══════════════════════════════════════════════════════════

def show_table_schema(conn: sqlite3.Connection, table_name: str):
    """显示表结构"""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    print(f"\n  📋 {table_name} 表结构:")
    for row in rows:
        nullable = "NULL" if row[3] else "NOT NULL"
        default = f" DEFAULT {row[4]}" if row[4] else ""
        print(f"     {row[1]:20s} {row[2]:10s} {nullable}{default}")

def show_data(conn: sqlite3.Connection, table_name: str):
    """显示表中数据"""
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    columns = [desc[1] for desc in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    print(f"\n  📊 {table_name} 数据 ({len(rows)} 行):")
    for row in rows:
        print(f"     ", end="")
        for col, val in zip(columns, row):
            print(f"{col}={val}  ", end="")
        print()


def main():
    DB_PATH = "./demo_migration.db"

    # 清理旧数据库
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    print("█" * 60)
    print("█  数据库迁移概念演示（迷你 Alembic）")
    print("█" * 60)

    # ═══════════════════════════════════════
    # 1. 初始化迁移引擎 + 注册版本
    # ═══════════════════════════════════════
    print("\n📦 1. 初始化迁移引擎，注册迁移版本")
    engine = MigrationEngine(DB_PATH)
    engine.register(Migration001_Initial())
    engine.register(Migration002_AddBio())
    engine.history()

    # ═══════════════════════════════════════
    # 2. 执行第一次迁移：创建初始表
    # ═══════════════════════════════════════
    print("\n" + "─" * 60)
    print("⬆ 2. 执行迁移 001: 创建 users 表")
    print("   (相当于 alembic upgrade 001_initial)")
    engine.upgrade("001_initial")
    engine.current()

    conn = sqlite3.connect(DB_PATH)
    show_table_schema(conn, "users")
    show_data(conn, "users")
    conn.close()

    # ═══════════════════════════════════════
    # 3. 执行第二次迁移：加 bio 和 avatar_url
    # ═══════════════════════════════════════
    print("\n" + "─" * 60)
    print("⬆ 3. 执行迁移 002: 新增 bio 和 avatar_url 字段")
    print("   (相当于 alembic upgrade head)")
    engine.upgrade("head")
    engine.current()

    conn = sqlite3.connect(DB_PATH)
    show_table_schema(conn, "users")
    show_data(conn, "users")
    conn.close()

    # ═══════════════════════════════════════
    # 4. 回滚第二次迁移
    # ═══════════════════════════════════════
    print("\n" + "─" * 60)
    print("⬇ 4. 回滚一步：撤销 bio 和 avatar_url")
    print("   (相当于 alembic downgrade -1)")
    engine.downgrade(steps=1)
    engine.current()

    conn = sqlite3.connect(DB_PATH)
    show_table_schema(conn, "users")
    show_data(conn, "users")
    conn.close()

    # ═══════════════════════════════════════
    # 5. 重新升级到最新
    # ═══════════════════════════════════════
    print("\n" + "─" * 60)
    print("⬆ 5. 重新升级到最新版本")
    print("   (相当于 alembic upgrade head)")
    engine.upgrade("head")
    engine.current()

    conn = sqlite3.connect(DB_PATH)
    show_table_schema(conn, "users")
    conn.close()

    # ═══════════════════════════════════════
    # 6. 最终状态
    # ═══════════════════════════════════════
    print("\n" + "=" * 60)
    print("📜 最终迁移历史")
    engine.history()
    engine.current()

    print("\n" + "=" * 60)
    print("✅ 演示结束！")
    print(f"   数据库文件: {DB_PATH}")
    print("   可删除它来重新运行本演示")
    print("\n💡 下一步：在真实项目中使用 Alembic")
    print("   参考本目录的 alembic_setup_guide.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
