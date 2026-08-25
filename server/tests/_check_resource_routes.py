"""ponytail: assert core resource alias routes are registered."""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "dev")

from main import create_app


def main() -> None:
    app = create_app()
    paths = {getattr(r, "path", "") for r in app.routes}
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
