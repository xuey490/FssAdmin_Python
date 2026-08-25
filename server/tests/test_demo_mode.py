"""ponytail: 演示模式必须拦住写操作，且 Settings 要真正读到 DEMO_ENABLE。"""

from app.config.setting import Settings
from app.core.middlewares import demo_write_allowed


def test_settings_has_demo_enable() -> None:
    assert Settings(DEMO_ENABLE=True).DEMO_ENABLE is True
    assert Settings(DEMO_ENABLE=False).DEMO_ENABLE is False


def test_demo_allows_read_and_login() -> None:
    assert demo_write_allowed("GET", "/api/platform/video/list", enabled=True)
    assert demo_write_allowed("OPTIONS", "/api/platform/video/delete/1", enabled=True)
    assert demo_write_allowed("POST", "/api/core/login", enabled=True)
    assert demo_write_allowed("POST", "/core/refresh", enabled=True)
    assert demo_write_allowed("POST", "/api/core/logout", enabled=True)


def test_demo_blocks_mutations() -> None:
    assert demo_write_allowed("DELETE", "/api/platform/video/delete/1", enabled=True) is False
    assert demo_write_allowed("PUT", "/api/platform/video/update/1", enabled=True) is False
    assert demo_write_allowed("POST", "/api/platform/video/create", enabled=True) is False
    assert demo_write_allowed("PATCH", "/api/system/user/update/1", enabled=True) is False
    # 关闭演示时全部放行
    assert demo_write_allowed("DELETE", "/api/platform/video/delete/1", enabled=False) is True


if __name__ == "__main__":
    test_settings_has_demo_enable()
    test_demo_allows_read_and_login()
    test_demo_blocks_mutations()
    print("ok")
