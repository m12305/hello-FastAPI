# 在真实项目中配置 Alembic

> 运行 `demo_migration.py` 理解迁移概念后，参考本指南在项目中配置真正的 Alembic。

## 快速上手

```bash
# 1. 安装
pip install alembic

# 2. 在项目根目录初始化（你的项目应该已有 models.py + database.py）
cd your_project/
alembic init alembic

# 3. 修改 alembic.ini 中的数据库 URL
# sqlalchemy.url = sqlite:///./app.db

# 4. 修改 alembic/env.py，导入你的 Base 和所有模型：
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# from database import Base, DATABASE_URL
# from models import User, Post  # 导入所有模型
# config.set_main_option("sqlalchemy.url", DATABASE_URL)
# target_metadata = Base.metadata

# 5. 生成迁移
alembic revision --autogenerate -m "初始化数据库"

# 6. 检查生成的迁移文件（alembic/versions/xxx.py），确认无误

# 7. 执行迁移
alembic upgrade head
```

## 日常开发工作流

```bash
# 修改 models.py → 生成迁移 → 检查 → 执行
alembic revision --autogenerate -m "描述你的改动"
# ... 检查 alembic/versions/ 中的新文件 ...
alembic upgrade head

# 回滚一步
alembic downgrade -1

# 查看当前版本
alembic current

# 查看完整历史
alembic history

# 查看要执行的 SQL（不实际执行）
alembic upgrade head --sql
```

## 常见问题

**Q: 提示 "Target database is not up to date"？**
A: 需要先执行迁移：`alembic upgrade head`

**Q: autogenerate 生成了空迁移文件？**
A: 检查 env.py 是否导入了所有模型，以及 models.py 确实有改动。

**Q: 之前用了 create_all()，现在想接上 Alembic？**
A: `alembic stamp head` 标记当前数据库状态为最新，跳过已有的表。
