# FssAdmin 后台管理系统（Python 版）

**Fast · Safe · Simple** — 基于 FastAPI + Vue 3 的开箱即用后台管理系统。

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-42b883?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646cff?logo=vite&logoColor=white)

前后端同仓：`server/` 为 Python 异步后端，`web/` 为 Vue 3 管理端，菜单与权限由后端下发。

在线预览：[https://fast.phpframe.org](https://fast.phpframe.org) · 默认账号 `admin` / 密码 `123456`

---



## 特点

- **竖切模块**：按业务分包（controller / service / crud / model / schema），而不是按技术层横切。
- **权限闭环**：用户 · 角色 · 菜单 · 部门 · 岗位（`post`）；接口 `AuthPermission`，前端 `VITE_ACCESS_MODE=backend` 动态路由。
- **多租户**：登录可选租户，支持按用户名查租户、切换租户（`module_system/tenant` → `sa_system_tenant`）。
- **会话可选**：JWT（access + refresh）或 Redis 不透明 Token。
- **运维面板**：服务监控、Redis、数据库、在线用户、登录/操作/邮件日志、附件、字典、参数配置。
- **演示模式**：`DEMO_ENABLE=True` 时拦截写操作（登录 / 刷新 / 登出除外）。
- **定时任务**：Cron 节点 + 调度器监控（`/task`）；内置操作日志清理、数据库备份。
- **视频下载**：yt-dlp 后台队列拉取元数据与文件（仅供学习，请勿用于非法用途）。

---



## 当前功能


| 模块      | 说明                  | API 前缀            |
| ------- | ------------------- | ----------------- |
| 认证 / 核心 | 登录、验证码、Token、站点配置   | `/core`           |
| 系统管理    | 用户、角色、菜单、部门、岗位、租户   | `/system`         |
| 系统运维    | 字典、附件、参数、登录/操作/邮件日志 | `/core`、`/system` |
| 监控      | 服务状态、Redis、数据库、在线用户 | `/monitor`        |
| 视频下载    | 链接录入、元数据、下载进度、预览    | `/platform/video` |
| 定时任务    | 任务节点、调度器任务与日志       | `/task/cronjob`   |
| 工作台     | 控制台、个人中心、示例仪表盘      | 前端静态路由            |
| 文章示例    | 示例 CRUD 页面          | 前端 + 菜单（视 SQL 种子） |
| 开发工具    | 代码生成 UI（后端插件未挂载）    | —                 |


认证：验证码登录、Token 刷新、登出、修改资料与密码。

### 已挂载的后端路由（`init_app.py`）

```
/common          健康检查
/core            登录、配置、日志
/monitor         服务 / 数据库 / 在线用户
/system          用户、角色、菜单、部门、岗位、租户、字典、附件
/platform/video  视频模块
/task            cronjob 节点 + 调度器
```

插件动态发现 **已关闭**；仅上述路由显式注册。

### 代码在仓、暂未挂载

以下目录仍保留源码或前端页面，但 **未注册到 FastAPI**，按需自行挂载：


| 路径                                  | 说明                                        |
| ----------------------------------- | ----------------------------------------- |
| `app/plugin/module_generator`       | 代码生成                                      |
| `app/plugin/module_example`         | 示例插件                                      |
| `app/api/v1/module_platform/plugin` | 平台插件市场（前端插件页目前走 `/api/system/plugin`，需对齐） |
| `app/api/v1/module_system/notice`   | 公告通知                                      |


---



## 技术栈



### 后端（`server/`）


| 技术                | 版本      | 用途                   |
| ----------------- | ------- | -------------------- |
| Python            | 3.13+   | 运行时                  |
| FastAPI           | 0.115   | HTTP / OpenAPI       |
| SQLAlchemy        | 2.x     | 异步 ORM               |
| Alembic           | 1.18    | 结构迁移（可选）             |
| Pydantic Settings | 2.x     | `.env.{dev,prod}` 配置 |
| Redis             | 客户端 7.x | 会话、缓存、限流             |
| Uvicorn           | 0.49    | ASGI                 |
| Typer             | 0.26    | `main.py` CLI        |
| APScheduler       | 3.11    | 定时任务（可关）             |
| yt-dlp            | 2026+   | 视频解析与下载              |
| uv                | —       | 依赖与启动（推荐）            |


数据库：MySQL 8 / PostgreSQL 13+ / SQLite（驱动：asyncmy、asyncpg、aiosqlite）。

### 前端（`web/`）


| 技术                | 版本     | 用途               |
| ----------------- | ------ | ---------------- |
| Vue               | 3.5    | UI               |
| Vite              | 8      | 构建与本地代理          |
| TypeScript        | 6      | 类型               |
| Element Plus      | 2.13   | 组件库              |
| Pinia             | 3      | 状态               |
| Vue Router        | 5      | Hash 路由          |
| Vue I18n          | 11     | 中 / 英            |
| Tailwind + UnoCSS | 4 / 66 | 样式               |
| pnpm              | ≥8.8   | 包管理（Node ≥20.19） |


界面基于 [Art Design Pro](https://www.artd.pro/) 管理端骨架。

---



## 仓库结构

```txt
FssAdmin_Python/
├── server/                   # 后端（在此目录执行 uv / main.py）
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── module_common/    # 健康检查
│   │   │   ├── module_system/    # 认证、用户、角色、菜单、租户…
│   │   │   ├── module_monitor/   # 监控、在线用户
│   │   │   └── module_platform/  # 视频（plugin 代码在仓未挂载）
│   │   ├── plugin/
│   │   │   ├── module_task/      # 定时任务（已挂载 /task）
│   │   │   ├── module_generator/ # 代码生成（未挂载）
│   │   │   └── module_example/   # 示例（未挂载）
│   │   ├── core/                 # 中间件、鉴权、调度器、数据库
│   │   ├── config/
│   │   ├── scripts/initialize.py # 手动 SQL 导入工具（启动时不调用）
│   │   └── alembic/
│   ├── database/fssoa.sql        # MySQL 种子（与仓库根 database/ 同步维护）
│   ├── static/backup/            # 数据库备份输出目录
│   ├── main.py
│   └── pyproject.toml
├── web/                      # Vue 管理端
└── database/fssoa.sql        # 根目录 SQL 副本（便于编辑）
```

业务模块分层：

```txt
module_*/
├── controller.py
├── service.py
├── crud.py          # 部分模块省略，直接用 service
├── model.py
└── schema.py
```

---



## 快速开始



### 环境

- Python **3.13+**，推荐 [uv](https://docs.astral.sh/uv/)
- MySQL / PostgreSQL / SQLite，以及 Redis（与 `.env.dev` 一致）
- Node.js **≥ 20.19**，pnpm **≥ 8.8**



### 后端

```bash
cd server
cp .env.dev.example .env.dev   # Windows: copy .env.dev.example .env.dev
# 填写 DATABASE_*、REDIS_*；先建好空库
# SERVER_PORT 与前端代理一致，开发常用 8001

uv sync
uv run main.py run --env=dev
```

**数据库初始化**：启动时 **不会** 自动导入 SQL。请手动导入：

```bash
mysql -h... -u... -p... 数据库名 < database/fssoa.sql
```

或在 Python 中调用 `InitializeData().init_db()`（见 `app/scripts/initialize.py`）。

API 文档（开发环境）：[http://127.0.0.1:8001/api/docs](http://127.0.0.1:8001/api/docs)

### 前端

```bash
cd web
pnpm install
# .env.development：VITE_API_URL=/api，代理到后端端口
pnpm run dev
```

生产构建：

```bash
cd web
pnpm run build
# dist/ 静态部署；/api 反代到后端 SERVER_PORT
```



### Alembic（可选）

```bash
cd server
set PYTHONIOENCODING=utf-8          # Windows 建议
uv run main.py revision --env=dev   # 生成迁移脚本，务必人工审阅
uv run main.py upgrade --env=dev    # 应用到数据库
```

若库来自完整 `fssoa.sql` 而 ORM 已精简，autogenerate 可能产生大量删表/改列操作，**不要未经审阅直接 upgrade**。日常表结构变更建议直接维护 `fssoa.sql`。

---



## 运行约定


| 项       | 说明                                                        |
| ------- | --------------------------------------------------------- |
| 环境文件    | `ENVIRONMENT=dev|prod` 加载 `server/.env.dev` / `.env.prod` |
| 接口前缀    | 如 `/core/login`、`/system/user`、`/platform/video/list`     |
| 开发热重载   | `--env=dev` 开启 uvicorn reload；生产用 `--env=prod`            |
| 限流 / 调度 | `.env` 中 `RATE_LIMIT_ENABLED`、`SCHEDULER_ENABLE`          |
| 系统定时任务  | 操作日志清理（周日 03:00）、数据库备份（每日 02:00 → `static/backup/`）       |
| 代码检查    | `cd server && uv run ruff check`                          |


---



## 插件约定

插件目录：`server/app/plugin/module_<name>/`，约定见 `app/core/discover.py` 文件头。

当前 **显式挂载** 的只有 `module_task`（cronjob）。其余插件需自行在 `init_app.register_routers` 中注册，或恢复动态发现机制。

---



## 相关链接

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Vue 3](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [Art Design Pro](https://www.artd.pro/)
- PHP 版：[https://v3.phpframe.org](https://v3.phpframe.org) · NestJs 版：[https://nest.phpframe.org](https://nest.phpframe.org)

