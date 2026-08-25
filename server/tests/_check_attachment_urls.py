"""ponytail: attachment url normalize + upload_mode dict ensure."""

from __future__ import annotations

import asyncio
import os

os.environ.setdefault("ENVIRONMENT", "dev")

from app.api.v1.module_system.attachment.service import normalize_attachment_url, strip_api_suffix
from app.api.v1.module_system.dict.service import DictService
from app.config.setting import get_settings
from app.core.database import async_db_session

get_settings.cache_clear()


def test_url() -> None:
    assert (
        normalize_attachment_url("http://localhost:8181/api/uploads/2026/07/17/a.jpg")
        == "http://localhost:8181/uploads/2026/07/17/a.jpg"
    )
    assert strip_api_suffix("http://localhost:8181/api") == "http://localhost:8181"
    assert strip_api_suffix("http://localhost:8181") == "http://localhost:8181"
    print("ok url")


async def test_dict() -> None:
    async with async_db_session() as db:
        svc = DictService(db=db)
        await svc.ensure_upload_mode_dict()
        await db.commit()
        data = await svc.get_all_data()
        items = data.get("upload_mode") or []
        vals = {str(i["value"]): i["label"] for i in items}
        assert "1" in vals and vals["1"], vals
        print("ok dict", vals)


if __name__ == "__main__":
    test_url()
    asyncio.run(test_dict())
