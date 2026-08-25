"""Check uploads mount + existing files."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "dev")

from app.config.path_conf import BASE_DIR
from main import create_app


def main() -> None:
    root = BASE_DIR / "uploads"
    files = list(root.rglob("*.*"))
    print("disk_count", len(files))
    for f in files[:5]:
        print("disk", f.relative_to(root))

    app = create_app()
    from starlette.testclient import TestClient

    client = TestClient(app)
    if not files:
        print("no files")
        return
    rel = files[0].relative_to(root).as_posix()
    url = f"/uploads/{rel}"
    r = client.get(url)
    print("get", url, "->", r.status_code, "ctype", r.headers.get("content-type"), "len", len(r.content))
    # missing
    r2 = client.get("/uploads/2026/07/17/1784245456548_719c70b7d36e4ce6.png")
    print("missing ->", r2.status_code)


if __name__ == "__main__":
    main()
