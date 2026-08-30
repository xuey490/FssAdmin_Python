"""ponytail: assert core resource alias routes are registered."""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "dev")

from fastapi.routing import iter_route_contexts

from main import create_app


def main() -> None:
    app = create_app()
    paths = {c.path for c in iter_route_contexts(app.routes) if c.path}
    need = (
        "/core/system/getResourceCategory",
        "/core/system/getResourceList",
        "/core/system/uploadImage",
    )
    missing = [p for p in need if p not in paths]
    assert not missing, f"missing={missing} paths={sorted(p for p in paths if 'Resource' in p or 'uploadImage' in p)}"
    print("ok", need)


if __name__ == "__main__":
    main()
