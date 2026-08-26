"""
模块接口测试 —— module_platform（平台管理）
认证数据测试：admin 登录后验证 CRUD 真实数据。
"""

from conftest import assert_route  # noqa: F401
from fastapi.testclient import TestClient


class TestPlugin:
    """插件管理接口。"""

    def test_plugin_list(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(test_client, "GET", "/platform/plugin/list", auth=auth_headers)

    def test_plugin_detail(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(test_client, "GET", "/platform/plugin/detail/1", auth=auth_headers)

    def test_plugin_create(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(
            test_client, "POST", "/platform/plugin/create", auth=auth_headers,
            json={"name": "测试插件", "code": "test_plugin"},
        )

    def test_plugin_update(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(
            test_client, "PUT", "/platform/plugin/update/1", auth=auth_headers,
            json={"name": "更新插件"},
        )

    def test_plugin_delete(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(test_client, "DELETE", "/platform/plugin/delete", auth=auth_headers, json=[9999])

    def test_plugin_marketplace(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(test_client, "GET", "/platform/plugin/marketplace", auth=auth_headers)

    def test_plugin_my(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(test_client, "GET", "/platform/plugin/my", auth=auth_headers)

    def test_plugin_install(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(
            test_client, "POST", "/platform/plugin/install", auth=auth_headers,
            json={"code": "test_plugin"},
        )

    def test_plugin_uninstall(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(
            test_client, "POST", "/platform/plugin/uninstall", auth=auth_headers,
            json={"code": "test_plugin"},
        )

    def test_plugin_toggle(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(
            test_client, "POST", "/platform/plugin/toggle", auth=auth_headers,
            json={"code": "test_plugin"},
        )

    def test_plugin_reload(self, test_client: TestClient, auth_headers: dict) -> None:
        assert_route(test_client, "POST", "/platform/plugin/reload", auth=auth_headers)
