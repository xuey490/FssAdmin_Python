"""兼容旧 route_class=OperationLogRoute。

操作日志已改为全局 OperationLogMiddleware（对齐 phpserver），此处仅透传，避免重复写库。
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.routing import APIRoute


class OperationLogRoute(APIRoute):
    """历史兼容：勿再依赖此类写日志。"""

    def get_route_handler(self) -> Callable:
        return super().get_route_handler()
