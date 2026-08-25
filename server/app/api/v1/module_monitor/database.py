"""数据表维护 /api/core/database/*，对齐 web + phpserver + NestJS。"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.common.response import ErrorResponse, SuccessResponse, page_result
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission

DatabaseRouter = APIRouter(tags=["数据库管理"])

_TABLE_RE = re.compile(r"^[a-zA-Z0-9_]+$")


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


def _fail(msg: str, code: int = 1) -> ErrorResponse:
    return ErrorResponse(msg=msg, code=code)


def _assert_debug() -> ErrorResponse | None:
    # 与 NestJS checkDebug 一致：非调试禁止远程看结构/改数据
    if not settings.DEBUG:
        return _fail("非开发模式，禁止远程访问数据结构", code=403)
    return None


def _valid_table(name: str) -> bool:
    return bool(name and _TABLE_RE.match(name))


def _format_bytes(n: int) -> str:
    if n <= 0:
        return "0 B"
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{round(n / 1024, 2)} KB"
    if n < 1024 * 1024 * 1024:
        return f"{round(n / 1024 / 1024, 2)} MB"
    return f"{round(n / 1024 / 1024 / 1024, 2)} GB"


def _fmt_dt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def _json_row(row: dict[str, Any]) -> str:
    def _default(o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return _fmt_dt(o)
        return str(o)

    return json.dumps(row, ensure_ascii=False, default=_default)


async def _fetch_all(db, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    result = await db.execute(text(sql), params or {})
    return [dict(r) for r in result.mappings().all()]


@DatabaseRouter.get("/core/database/table/list")
async def table_list(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:database:index"])),
):
    name = str(request.query_params.get("name") or "").strip()
    rows = await _fetch_all(auth.db, "SHOW TABLE STATUS")
    list_: list[dict[str, Any]] = []
    for row in rows:
        table_name = str(row.get("Name") or "")
        if name and name.lower() not in table_name.lower():
            continue
        data_free = int(row.get("Data_free") or 0)
        data_length = int(row.get("Data_length") or 0) + int(row.get("Index_length") or 0)
        list_.append(
            {
                "name": table_name,
                "comment": row.get("Comment") or "",
                "engine": row.get("Engine") or "",
                "rows": int(row.get("Rows") or 0),
                "data_free": _format_bytes(data_free),
                "data_length": _format_bytes(data_length),
                "collation": row.get("Collation") or "",
                "create_time": _fmt_dt(row.get("Create_time")),
                "update_time": _fmt_dt(row.get("Update_time")),
            }
        )
    return _ok({"list": list_, "total": len(list_)})


@DatabaseRouter.get("/core/database/table/dataSource")
async def data_source(auth: AuthSchema = Depends(AuthPermission(permissions=["core:database:index"]))):
    db_type = getattr(settings, "DATABASE_TYPE", None) or "mysql"
    return _ok([str(getattr(db_type, "value", db_type))])


@DatabaseRouter.get("/core/database/table/detailed")
async def table_detailed(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:database:index"])),
):
    if err := _assert_debug():
        return err
    table = str(request.query_params.get("table") or request.query_params.get("tableName") or "")
    if not table:
        return _fail("表名不能为空")
    if not _valid_table(table):
        return _fail("表名格式不正确")
    rows = await _fetch_all(auth.db, f"SHOW FULL COLUMNS FROM `{table}`")
    columns = [
        {
            "column_name": r.get("Field") or "",
            "column_type": r.get("Type") or "",
            "column_key": r.get("Key") or "",
            "is_nullable": (r.get("Null") or "") == "YES",
            "column_default": r.get("Default"),
            "column_comment": r.get("Comment") or "",
        }
        for r in rows
    ]
    return _ok({"columns": columns})


@DatabaseRouter.get("/core/database/table/createSql")
async def create_sql(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:database:index"])),
):
    if err := _assert_debug():
        return err
    table = str(request.query_params.get("table") or request.query_params.get("tableName") or "")
    if not table:
        return _fail("表名不能为空")
    if not _valid_table(table):
        return _fail("表名格式不正确")
    rows = await _fetch_all(auth.db, f"SHOW CREATE TABLE `{table}`")
    if not rows:
        return _ok({"table": table, "sql": ""})
    row = rows[0]
    sql = row.get("Create Table") or row.get("Create View") or ""
    return _ok({"table": table, "sql": sql})


@DatabaseRouter.post("/core/database/table/optimize")
async def optimize_table(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:database:edit"])),
):
    if err := _assert_debug():
        return err
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    tables = body.get("tables") or body.get("tableNames") or []
    if not tables:
        return _fail("请选择要优化的表")
    results: dict[str, dict[str, Any]] = {}
    for table in tables:
        if not _valid_table(str(table)):
            return _fail(f"表名格式不正确: {table}")
        try:
            await auth.db.execute(text(f"OPTIMIZE TABLE `{table}`"))
            results[str(table)] = {"success": True}
        except Exception as e:
            results[str(table)] = {"success": False, "message": str(e)}
    return _ok(results, "优化完成")


@DatabaseRouter.post("/core/database/table/fragment")
async def clean_fragment(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:database:edit"])),
):
    if err := _assert_debug():
        return err
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    tables = body.get("tables") or body.get("tableNames") or []
    if not tables:
        return _fail("请选择要清理的表")
    results: dict[str, dict[str, Any]] = {}
    for table in tables:
        if not _valid_table(str(table)):
            return _fail(f"表名格式不正确: {table}")
        try:
            await auth.db.execute(text(f"OPTIMIZE TABLE `{table}`"))
            await auth.db.execute(text(f"ANALYZE TABLE `{table}`"))
            results[str(table)] = {"success": True}
        except Exception as e:
            results[str(table)] = {"success": False, "message": str(e)}
    return _ok(results, "清理完成")


@DatabaseRouter.get("/core/database/recycle/list")
async def recycle_list(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:recycle:index"])),
):
    table = str(request.query_params.get("table") or "")
    try:
        page = max(1, int(request.query_params.get("page") or 1))
    except ValueError:
        page = 1
    try:
        limit = max(1, int(request.query_params.get("limit") or 20))
    except ValueError:
        limit = 20

    empty = page_result([], 0, page, limit)
    if not table:
        return _ok(empty)
    if not _valid_table(table):
        return _fail("表名格式不正确")

    cols = await _fetch_all(auth.db, f"DESCRIBE `{table}`")
    if not any((c.get("Field") == "delete_time") for c in cols):
        return _ok(empty)

    count_rows = await _fetch_all(
        auth.db, f"SELECT COUNT(*) AS cnt FROM `{table}` WHERE delete_time IS NOT NULL"
    )
    total = int((count_rows[0] or {}).get("cnt") or 0)
    offset = (page - 1) * limit
    rows = await _fetch_all(
        auth.db,
        f"SELECT * FROM `{table}` WHERE delete_time IS NOT NULL "
        f"ORDER BY delete_time DESC LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset},
    )
    list_ = [
        {
            "id": r.get("id"),
            "delete_time": _fmt_dt(r.get("delete_time")),
            "json_data": _json_row(r),
        }
        for r in rows
    ]
    return _ok(page_result(list_, total, page, limit))


@DatabaseRouter.post("/core/database/recycle/destroy")
async def recycle_destroy(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:recycle:edit"])),
):
    if err := _assert_debug():
        return err
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    table = str(body.get("table") or "")
    ids = _parse_ids(body.get("ids"))
    if not table or not ids:
        return _fail("参数不完整")
    if not _valid_table(table):
        return _fail("表名格式不正确")
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": vid for i, vid in enumerate(ids)}
    await auth.db.execute(text(f"DELETE FROM `{table}` WHERE id IN ({placeholders})"), params)
    return _ok([], "销毁成功")


@DatabaseRouter.post("/core/database/recycle/recovery")
async def recycle_recovery(
    request: Request,
    auth: AuthSchema = Depends(AuthPermission(permissions=["core:recycle:edit"])),
):
    if err := _assert_debug():
        return err
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    table = str(body.get("table") or "")
    ids = _parse_ids(body.get("ids"))
    if not table or not ids:
        return _fail("参数不完整")
    if not _valid_table(table):
        return _fail("表名格式不正确")
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": vid for i, vid in enumerate(ids)}
    await auth.db.execute(
        text(f"UPDATE `{table}` SET delete_time = NULL WHERE id IN ({placeholders})"),
        params,
    )
    return _ok([], "恢复成功")


def _parse_ids(raw: Any) -> list[int]:
    out: list[int] = []
    for x in raw or []:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out
