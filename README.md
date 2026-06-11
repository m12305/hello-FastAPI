<div align='center'>
  <h1 style="margin-top: 15px;">⚡ FastAPI 从零到企业级项目开发</h1>
  <h4><b>hello-FastAPI</b></h4>
  <p><em>2026 持续更新中 · 面向 Python 开发的 FastAPI 系统入门教程 —— <b>从类型标注到部署运维</b>，39 章 + 3 个实战项目，覆盖企业级 API 开发全流程</em></p>
</div>

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat)
![Docs](https://img.shields.io/badge/docs-Chinese-2ea44f?style=flat)
![Status](https://img.shields.io/badge/status-updating-orange?style=flat)

[快速开始](#-快速开始) · [学习路线](FastAPI学习路线.md) · [学习方法](FastAPI学习方法.md) · [学习进度](FastAPI学习进度.md)

</div>

---

## 📖 关于本项目

市面上不缺 FastAPI 教程，本项目的目标是**做一套有体系的、从零到企业级的 FastAPI 学习路径**——每个概念都有完整的文字讲解 + 可运行的代码 Demo，让你不仅能看懂，更能动手跑起来。

> **默认读者**：熟悉 Python 基础语法，想系统学习 FastAPI 后端开发的开发者。如果你完全没接触过 Python，建议先花一周过一遍基础语法。

---

## ✨ 项目亮点

- **🗺️ 体系化路线**：10 个阶段、39 章 + 3 个实战项目，从 Python 类型标注到 Docker 部署，按学习曲线编排
- **📝 逐章精讲**：每个章节都是一篇独立的 `.md` 教程，包含概念讲解、代码示例、对比表格、检查清单
- **✅ 每章可运行**：每个阶段提供独立可运行的代码 Demo，`uvicorn main:app --reload` 一键启动
- **🧠 六步学习法**：每个章节配套 [六步学习法](FastAPI学习方法.md)（读 → 敲 → 改 → 测 → 查 → 总结），确保真正掌握
- **🎯 贴近实战**：不是玩具代码——文件上传含魔数检测、依赖注入含工厂模式、中间件含限流器
- **🌐 中文友好**：所有文档和注释使用中文，变量名使用英文，降低理解门槛

---

## 🛠 技术栈概览

| 类别 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | FastAPI 0.115+ | 现代、高性能、异步 Python Web 框架 |
| **ASGI 服务器** | Uvicorn | FastAPI 官方推荐的 ASGI 服务器 |
| **数据校验** | Pydantic v2 | 类型安全的数据验证，FastAPI 的基石 |
| **数据库** | SQLAlchemy 2.0 + Alembic | ORM + 数据库迁移（阶段 3） |
| **认证** | JWT + OAuth2 | Token 认证与权限控制（阶段 4） |
| **模板引擎** | Jinja2 | 服务端页面渲染 |
| **缓存** | Redis | 缓存策略与分布式锁（阶段 7） |
| **任务队列** | Celery | 异步任务处理（阶段 9） |
| **容器化** | Docker + Docker Compose | 一键部署（阶段 8） |
| **CI/CD** | GitHub Actions | 自动化测试与部署（阶段 8） |

---

## 🎯 你学完能收获什么？

- **独立开发 RESTful API**：能基于 FastAPI 从零搭建结构清晰、校验完善的后端服务
- **理解异步编程**：掌握 `async/await` 在 Web 开发中的实际应用
- **掌握依赖注入**：FastAPI 最核心的概念——能用依赖注入管理认证、数据库、权限等横切关注点
- **数据库工程化**：能用 SQLAlchemy + Alembic 做数据持久化和版本迁移
- **安全最佳实践**：JWT 认证、RBAC 权限控制、CORS 配置、速率限制
- **生产部署能力**：Docker 容器化、Nginx 反向代理、CI/CD 流水线

---

## 📚 项目大纲

完整导航见 **[FastAPI学习路线](FastAPI学习路线.md)**。

| 阶段 | 主题 | 章节 | 状态 |
|------|------|------|------|
| **0** | 前置基础 | Python 类型标注 · 异步编程 · HTTP 协议 · Pydantic | ✅ 已完成 |
| **1** | FastAPI 核心 | Hello World · 路径操作 · 查询参数 · 响应模型 · 错误处理 | ✅ 已完成 |
| **2** | 请求与响应 | 高级验证 · Header/Cookie/表单/文件上传 · 依赖注入 · 中间件与 CORS · 静态文件与模板 | ✅ 已完成 |
| **3** | 数据库与 ORM | SQLAlchemy 基础 · 集成 FastAPI · Alembic 迁移 · 异步数据库 · 高级话题 | 🚧 规划中 |
| **4** | 认证与授权 | 认证基础 · JWT · 权限控制 · 安全最佳实践 | 🚧 规划中 |
| **5** | 测试 | TestClient · Mock 与依赖覆盖 · CI 集成 | 🚧 规划中 |
| **6** | 高级特性 | 后台任务 · WebSocket · 生命周期 · API 版本化 · 性能优化 | 🚧 规划中 |
| **7** | 架构设计 | 项目结构 · 配置管理 · 日志系统 · 缓存策略 | 🚧 规划中 |
| **8** | 部署运维 | Docker · CI/CD · Nginx · 监控 | 🚧 规划中 |
| **9** | 实战项目 | Todo API · 博客系统 · 电商 API | 🚧 规划中 |

> 每个阶段包含：📖 逐章教程文档（`.md`） → 💻 可运行代码 Demo（`main.py`）→ ✅ 检查清单

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- pip（Python 包管理器）
- （可选）虚拟环境工具 `venv` 或 `conda`

### 1. 克隆仓库

```bash
git clone https://github.com/xiaoma/hello-FastAPI.git
cd hello-FastAPI
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install fastapi uvicorn[standard]
# 阶段 2.5 需要额外安装：
pip install jinja2 aiofiles
```

### 4. 运行第一个 Demo

```bash
# 运行阶段 1 的 Hello World
cd code/阶段1-FastAPI核心
uvicorn 1.1_hello_world:app --reload
```

然后访问 `http://127.0.0.1:8000/docs` 查看交互式 API 文档。

### 5. 按推荐顺序学习

```
1. 阅读 FastAPI学习方法.md       → 了解六步学习法
2. 阅读 FastAPI学习路线.md       → 了解整体学习路径
3. 从 阶段0 开始逐个阶段学习      → 每个阶段：读文档 → 跑代码 → 做练习 → 勾选检查清单
```

---

## 📂 项目结构

```
hello-FastAPI/
├── README.md                     ← 📖 项目主页
├── FastAPI学习路线.md            ← 🗺️ 完整学习大纲（10 个阶段）
├── FastAPI学习方法.md            ← 🧠 六步学习法
├── FastAPI学习进度.md            ← ✅ 学习进度追踪
│
├── 阶段0-前置基础/               ← 📝 4 章教程文档
├── 阶段1-FastAPI核心/            ← 📝 5 章教程文档
├── 阶段2-请求与响应/              ← 📝 5 章教程文档 
│
└── code/                         ← 💻 代码 Demo
    ├── 阶段1-FastAPI核心/
    └── 阶段2-请求与响应/
```

---

## 📖 关于本仓库

- **目标**：做一套真正适合 Python 开发者的 FastAPI 系统入门学习路线，覆盖从基础概念到企业级部署的全流程
- **技术定位**：聚焦 FastAPI 生态，从框架核心到周边工具（Pydantic、SQLAlchemy、Redis、Docker）完整串联
- **内容来源**：官方文档精读 + 社区最佳实践 + 实战经验总结
- **内容构成**：**系统教程**（`.md` 逐章讲解） + **可运行源码**（每个 Demo 独立可跑） + **检查清单**（每章自查）
- **更新频率**：2026 年持续更新中，按学习路线逐阶段推进

---

## ⭐ 如果对你有帮助

如果本教程对你的 FastAPI 学习有帮助，欢迎 **Star** ⭐ ~

也欢迎提 Issue、PR 一起完善内容！

---

**仓库名**：`hello-FastAPI` · **中文名**：《FastAPI 从零到企业级项目开发》
