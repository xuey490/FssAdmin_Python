"""ponytail: smoke check for database maintain APIs (no HTTP)."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.api.v1.module_monitor.database import (
    _format_bytes,
    _fmt_dt,
    _parse_ids,
    _valid_table,
)
from app.core.database import async_db_session


async def main() -> None:
    assert _valid_table("sa_system_user")
    assert not _valid_table("a;drop")
    assert _format_bytes(0) == "0 B"
    assert _parse_ids(["1", 2, "x"]) == [1, 2]

    async with async_db_session() as db:
        async with db.begin():
            rows = (await db.execute(text("SHOW TABLE STATUS"))).mappings().all()
            assert rows, "no tables"
            name = "sa_system_user"
            cols = (await db.execute(text(f"SHOW FULL COLUMNS FROM `{name}`"))).mappings().all()
            assert cols, "no columns"
            create = (await db.execute(text(f"SHOW CREATE TABLE `{name}`"))).mappings().all()
            assert create and (create[0].get("Create Table") or create[0].get("Create View"))
            sample = dict(rows[0])
            print(
                "ok",
                len(rows),
                "tables;",
                name,
                len(cols),
                "cols;",
                _format_bytes(int(sample.get("Data_length") or 0)),
                _fmt_dt(sample.get("Create_time")),
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("FAIL:", e, file=sys.stderr)
        raise SystemExit(1)
