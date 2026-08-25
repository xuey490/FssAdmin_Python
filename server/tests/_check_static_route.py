"""Assert /static FileResponse works under root_path=/api (StaticFiles Mount does not)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ENVIRONMENT", "dev")

from starlette.testclient import TestClient

from app.config.setting import settings
from main import create_app


def main() -> None:
    root = Path(settings.STATIC_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    probe = root / "_static_route_probe.txt"
    probe.write_text("ok", encoding="utf-8")
    try:
        client = TestClient(create_app())
        r = client.get("/static/_static_route_probe.txt")
        assert r.status_code == 200 and r.text == "ok", (r.status_code, r.text)
        print("static_route_ok")
    finally:
        probe.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
