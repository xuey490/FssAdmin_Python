"""Compare DB attachment urls vs disk files."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "dev")

from sqlalchemy import text

from app.config.path_conf import BASE_DIR
from app.config.setting import get_settings
from app.core.database import async_db_session

get_settings.cache_clear()


async def main() -> None:
    root = BASE_DIR / "uploads"
    async with async_db_session() as db:
        rows = (
            await db.execute(
                text(
                    "select id, url, storage_path from sa_system_attachment "
                    "where delete_time is null order by id desc limit 8"
                )
            )
        ).fetchall()
    for rid, url, sp in rows:
        p = root / Path(str(sp).removeprefix("uploads/").replace("\\", "/"))
        # storage_path is uploads/Y/m/d/file
        p2 = BASE_DIR / str(sp).replace("\\", "/")
        exists = p2.is_file()
        print(f"id={rid} exists={exists} path={sp} url={url}")


if __name__ == "__main__":
    asyncio.run(main())
