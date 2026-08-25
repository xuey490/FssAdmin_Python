# FssAdmin后台管理系统（python版）

**Fast · Safe · Simple** — 基于 FastAPI + Vue 3 的开箱即用后台管理系统。

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-8-646cff?logo=vite&logoColor=white)](https://vite.dev/)

前后端同仓：Python 异步后端提供 RBAC、多租户、运维监控与业务插件；`web/` 是 Vue 3 管理端，菜单由后端下发。

在线预览：<https://fast.phpframe.org> 默认账号:admin , 密码： 123456

---

## 特点

- **竖切模块**：按业务分包（controller / service / crud / model / schema），而不是按技术层横切。
- **权限闭环**：用户 · 角色 · 菜单 · 部门 · 岗位；接口 `AuthPermission`，前端 `VITE_ACCESS_MODE=backend` 按菜单动态路由。
- **多租户**：登录可选租户，支持按用户名查租户、切换租户。
- **会话可选**：JWT（access + refresh，可滑动过期）或 Redis 不透明 Token。
- **运维面板**：服务监控、Redis、数据库、在线用户、登录/操作/邮件日志、附件、字典、参数配置。
- **演示模式**：`DEMO_ENABLE=True` 时拦截写操作（登录 / 刷新 / 登出除外）。
- **插件目录**：`app/plugin/module_*` 约定扫描；定时任务已挂载，代码生成、AI 对话按插件扩展。
- **视频下载**：yt-dlp 后台队列拉取元数据与文件（可以下载油管，B站，小红书，X，脸书等多个网站的视频，仅用于学习，请勿用于非法用途）。

---

## 功能一览

| 模块 | 说明 |
|------|------|
| 工作台 | 控制台、个人中心 |
| 系统管理 | 用户、角色、菜单、部门、岗位、租户、插件 |
| 系统运维 | 服务监控、缓存 / Redis、数据库、附件、字典、在线用户、登录日志、操作日志、邮件日志 |
| 视频下载 | 批量录入链接、元数据抓取、格式选择、下载进度、本地预览 |
| 定时任务 | Cron 节点与任务（`/task`） |
| AI 助手（有待完善） | 对话 / 供应商 / 模型配置页面（后端以 `module_ai` 插件提供） |
| 开发工具（有待完善） | 代码生成、文章示例页 |

认证相关：验证码登录、Token 刷新、登出、修改资料与密码。

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.13+ | 运行时 |
| FastAPI | 0.115 | HTTP / OpenAPI |
| SQLAlchemy | 2.x | 异步 ORM |
| Alembic | 1.18 | 结构迁移 |
| Pydantic Settings | 2.x | `.env.{dev,prod}` 配置 |
| Redis | 客户端 7.x | 会话、缓存、限流 |
| Uvicorn | 0.49 | ASGI |
| Typer | 0.26 | `main.py` CLI |
| APScheduler | 3.11 | 定时任务（可关） |
| yt-dlp | 2026+ | 视频解析与下载 |
| uv | — | 依赖与启动（推荐） |

数据库：MySQL 8 / PostgreSQL 13+ / SQLite。驱动分别为 asyncmy、asyncpg、aiosqlite。

### 前端（`web/`）

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5 | UI |
| Vite | 8 | 构建与本地代理 |
| TypeScript | 6 | 类型 |
| Element Plus | 2.13 | 组件库 |
| Pinia | 3 | 状态（可持久化） |
| Vue Router | 5 | Hash 路由 |
| Vue I18n | 11 | 中 / 英 |
| Tailwind CSS + UnoCSS | 4 / 66 | 样式 |
| Axios | 1.16 | 请求，`baseURL = VITE_API_URL` |
| ECharts / VXE Table | — | 图表与表格 |
| pnpm | ≥8.8 | 包管理（Node ≥20.19） |

界面基于 [Art Design Pro](https://www.artd.pro/) 管理端骨架，业务接口对齐本仓库 FastAPI。

---

## 仓库结构

```txt
FastAdmin/
├── app/                      # 后端
│   ├── api/v1/
│   │   ├── module_common/    # 健康检查
│   │   ├── module_system/    # 认证、用户、角色、菜单、租户…
│   │   ├── module_monitor/   # 服务 / 数据库 / 在线用户
│   │   └── module_platform/  # 视频等平台能力
│   ├── plugin/               # 插件（module_task / module_ai / module_generator …）
│   ├── core/                 # 中间件、鉴权、数据库、限流
│   ├── config/               # Settings
│   ├── scripts/              # 空库导入 database/fssoa.sql
│   └── utils/
├── database/fssoa.sql        # MySQL 种子库
├── web/                      # Vue 管理端
├── tests/                    # pytest
├── main.py                   # uv run main.py run --env=dev
├── pyproject.toml            # uv / ruff
└── .env.dev.example          # 复制为 .env.dev
```

业务模块分层：

```txt
module_*/
├── controller.py
├── service.py
├── crud.py
├── model.py
├── schema.py
└── param.py          # 部分模块
```

---

## 快速开始

### 运行环境

- Python **3.13+**，推荐 [uv](https://docs.astral.sh/uv/)
- MySQL / PostgreSQL / SQLite，以及 Redis（与 `.env.dev` 一致）
- Node.js **≥ 20.19**，pnpm **≥ 8.8**

### 后端部署

```bash
cp .env.dev.example .env.dev   # Windows: copy .env.dev.example .env.dev
# 填写 DATABASE_*、REDIS_*；先建好空库
# SERVER_PORT 与前端代理一致，本仓库开发常用 8001

uv sync
uv run main.py run --env=dev
```

首次启动会检测空库并导入 `database/fssoa.sql`（MySQL）。文档地址以启动面板为准，一般为：

```txt
http://127.0.0.1:8001/api/docs
```

或：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
python main.py run --env=dev
```

模型变更后再用 Alembic：

```bash
uv run main.py revision --env=dev
uv run main.py upgrade --env=dev
```

种子用户为 `admin`。导入 SQL 后请立即修改密码；不要把生产 `.env` 提交进仓库。

### 前端部署

```bash
cd web
pnpm install
# web/.env.development 中 VITE_API_URL=/api，Vite 代理到 VITE_API_PROXY_URL（默认 8001）
pnpm run dev
```

生产构建：

```bash
cd web
# .env.production 中 VITE_API_URL=/api（与 Nginx 反代目录一致）
pnpm run build
```

`dist/` 部署到静态站点；把 **`/api` 反代到** `http://127.0.0.1:<SERVER_PORT>`。前端接口路径已带 `/api/core/...`，`VITE_API_URL` 只表示网关前缀，不要再叠一层 `/nest-api` 之类路径，除非网关会剥掉该前缀。

---

## 运行约定

| 项 | 说明 |
|----|------|
| 环境文件 | `ENVIRONMENT=dev\|prod` 加载 `.env.dev` / `.env.prod` |
| 真实路由 | 如 `/core/login`、`/system/user`、`/platform/video/list`（`ROOT_PATH` 主要用于文档前缀） |
| 开发热重载 | `--env=dev` 开启 uvicorn reload；**进程守护 / systemd 请用 `--env=prod`**，否则父进程监视文件容易被判退出 |
| 限流 / 调度 | `.env` 中 `RATE_LIMIT_ENABLED`、`SCHEDULER_ENABLE` |
| 代码检查 | `uv run ruff check` |

---

## 插件约定

放在 `app/plugin/module_<name>/`，控制器必须是顶层 `APIRouter` 的 `controller.py`。前缀为 `/<name>`（去掉 `module_`）。详见 `app/core/discover.py` 文件头注释。

当前显式挂载：系统路由、监控、视频、`/task` 定时任务。其余插件按发现机制或后续接入。

---

## 相关链接

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Vue 3](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [Art Design Pro](https://www.artd.pro/)
