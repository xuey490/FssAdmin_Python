# FastAdmin (FssAdmin) — Project Rules

Enterprise multi-tenant admin **backend** built with FastAPI. This directory is the Python API service (not NestJS). Prefer matching existing module patterns over inventing new structure.

## 语言与回复

- **最终回答必须用中文**：结论、总结、变更说明、操作指引、错误说明等面向用户的最终输出一律使用中文。
- **过程可用中英混合**：分析、推理、工具调用说明、代码标识符（路径、类名、命令）可中英混用；代码本身保持项目原有语言风格。
- 技术专有名词（FastAPI、SQLAlchemy、Redis 等）可保留英文，但整句说明用中文组织。

## Stack

| Layer | Choice |
|-------|--------|
| Runtime | Python **3.12+** |
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy **2.x** (async) |
| Migrations | Alembic |
| Validation | Pydantic **v2** |
| Cache / session | Redis |
| Scheduler | APScheduler |
| Package manager | **uv** (`pyproject.toml` + `uv.lock`) preferred; `requirements.txt` for prod |
| Lint / format | **ruff** (line-length 200, 4-space indent, double quotes) |

## Commands

Run from this directory (project root of the backend):

```bash
# Install (includes dev group: pytest, ruff, fakeredis)
uv sync

# Dev server (default env=dev; reloads on code change)
uv run main.py run --env=dev
# or: python main.py run --env=dev

# Alembic after ORM model changes
uv run main.py revision --env=dev
uv run main.py upgrade --env=dev

# Lint
uv run ruff check
uv run ruff check --fix

# Tests
uv run pytest
```

Config: copy `.env.dev.example` → `.env.dev` (DB, Redis, `SERVER_PORT`, etc.). First start auto-inits tables/seed data via `InitializeData`. API docs: `{host}:{port}/docs` (port from env, example `8181`). Root path prefix often `/api` (`ROOT_PATH`).

Do **not** commit real secrets in `.env.dev` / `.env.prod`. Use the `*.example` files as templates only.

## Layout

```text
main.py                 # Typer CLI: run / revision / upgrade; create_app()
app/
  api/v1/
    module_system/      # auth, user, role, dept, menu, dict, logs, …
    module_platform/    # tenant, package, plugin, order, email, invoice, …
    module_monitor/     # online users, server/DB health
    module_common/      # file upload, health
  plugin/               # secondary-dev plugins (dynamic routes)
    module_*/…/controller.py
  core/                 # DB, auth, middleware, base CRUD/model/schema, permissions
  common/               # response, enums, constants
  config/               # settings, paths
  scripts/              # DB init + JSON seed data
  utils/                # captcha, upload, excel, email, …
tests/                  # pytest + TestClient; conftest forces SQLite + mock Redis
```

### Business module layering

New features under `app/api/v1/module_*` should follow existing packages:

| File | Role |
|------|------|
| `controller.py` | HTTP routes only; thin handlers |
| `service.py` | Business logic; takes `AuthSchema` |
| `crud.py` | DB access (when used; some modules use service + SQLAlchemy directly) |
| `model.py` | SQLAlchemy models |
| `schema.py` | Pydantic request/response models |
| `__init__.py` | Wire `APIRouter` into the module router |

Register new routers in the parent module’s `__init__.py` (e.g. `module_system` → prefix `/system`, `module_platform` → `/platform`).

### Plugins (`app/plugin`)

- Top-level dir **must** be `module_<name>` (e.g. `module_example`).
- Controllers must be named `controller.py` and define a top-level `APIRouter` variable.
- Route prefix becomes `/<name>` (strip `module_`).
- Optional `plugin.toml` for metadata only; runtime deps stay in root `pyproject.toml`.
- See comments in `app/core/discover.py` for scan rules.

## Coding conventions

### Controllers

- Use `APIRouter(route_class=OperationLogRoute, prefix="...", tags=[...])` when other modules do.
- Auth: `Depends(get_current_user)` for login-only; `Depends(AuthPermission())` for permission-checked writes.
- Return `SuccessResponse` / `ErrorResponse` from `app.common.response` (business `code=200` success; failures often HTTP 200 + non-200 `code`, except auth 401).
- Prefer thin controllers: parse body/query → call service → wrap response. Mirror nearby modules (many use `_ok()` + `await request.json()` helpers).

### Services & data

- Service constructors take `AuthSchema`; use `auth.db` for `AsyncSession`.
- Multi-tenant: filter by `tenant_id` from auth; soft-delete via `delete_time` / `not_deleted(Model)`.
- Prefer async SQLAlchemy (`select`, `await db.execute`).
- Models: extend `SaModelMixin` (id + create/update/delete time) and `TenantMixin` when row-level tenant applies (`app.core.base_model`).
- Raise `CustomException` for domain errors; controllers map to `ErrorResponse`.

### Serialization

- Pydantic v2: `model_dump(mode='python')` for ORM; `model_dump(mode='json')` for JSON/Redis.
- Date types: use project validators in `app.core.validator` (`DateStr` / `TimeStr` / `DateTimeStr` with `when_used='json'`).
- HTTP encoding: `jsonable_encoder` path in `app.common.response`.

### Style

- Match surrounding code: Chinese docstrings/comments are common; keep new public API messages consistent with existing Chinese UX strings where the module already uses them.
- Ruff is authoritative; do not fight ignored rules in `pyproject.toml`.
- Avoid drive-by refactors outside the task. Do not add unsolicited docs/markdown.

## Auth & tenancy (do not break)

- Token modes: `SESSION_TYPE=jwt` or `redis-token` (see settings).
- Tenant resolution: JWT `tenant_id` first; else `X-Tenant-Id` header (`get_current_user` in `app.core.dependencies`).
- Superadmin checks: `require_superadmin` / `user.is_super`.
- Demo mode: `DEMO_ENABLE` may restrict writes—respect existing guards.

## Testing

- `tests/conftest.py` sets SQLite + mocked Redis and disables captcha; keep that isolation.
- Prefer `TestClient` and existing `test_api_module_*.py` patterns when adding API coverage.
- Run targeted tests when possible: `uv run pytest tests/test_api_module_system.py -q`.

## Safety / hygiene

- Do not modify seed JSON in `app/scripts/data/` unless the task is about init data.
- Do not put secrets, production credentials, or large binaries in the repo.
- Prefer `uv run` so the project env matches `uv.lock`.
- After model changes, generate/apply Alembic migrations rather than hand-editing production DBs.

## Quick orientation

| Goal | Start here |
|------|------------|
| Login / JWT | `app/api/v1/module_system/auth/` |
| Users / roles / menus | `app/api/v1/module_system/` |
| Tenants / packages / orders | `app/api/v1/module_platform/` |
| App factory / middleware | `main.py`, `app/init_app.py` |
| Settings | `app/config/setting.py`, `.env.*` |
| Shared response / RET codes | `app/common/response.py`, `app/common/constant.py` |
| Plugin example | `app/plugin/module_example/` |
