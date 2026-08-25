"""ponytail: assert captcha image generation + response shape for web login."""

from __future__ import annotations

import base64
import os

os.environ.setdefault("ENVIRONMENT", "dev")

from app.utils.captcha_util import CaptchaUtil


def main() -> None:
    img_b64, code = CaptchaUtil.generate_captcha()
    assert isinstance(code, str) and len(code) == 4, code
    raw = base64.b64decode(img_b64)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    image = f"data:image/png;base64,{img_b64}"
    assert image.startswith("data:image/png;base64,")
    print("ok", "code=", code, "png_bytes=", len(raw))


if __name__ == "__main__":
    main()
