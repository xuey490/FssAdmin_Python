from math import ceil
from typing import NoReturn, Union

from fastapi import Request, Response
from starlette.websockets import WebSocket

from app.core.exceptions import CustomException


async def ip_identifier(request: Union[Request, WebSocket]) -> str:
    """按客户端 IP 限流（不按 path 拆分，对齐全局限流语义）。"""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def http_limit_callback(request: Request, response: Response, expire: int) -> NoReturn:
    """
    HTTP 触发限流时的默认回调：抛出 429。

    参数:
    - request (Request): 当前请求。
    - response (Response): 当前响应（未直接使用，保留与限流器签名一致）。
    - expire (int): 剩余冷却毫秒数。

    返回:
    - 无（始终抛出 CustomException）。
    """
    expires = ceil(expire / 30)
    raise CustomException(
        status_code=429,
        msg="请求过于频繁，请稍后重试！",
        data={"Retry-After": str(expires)},
    )


async def ws_limit_callback(ws: WebSocket, expire: int) -> None:
    """
    WebSocket 触发限流时的默认回调：关闭连接。

    参数:
    - ws (WebSocket): 当前 WebSocket。
    - expire (int): 剩余冷却毫秒数。

    返回:
    - None
    """
    expires = ceil(expire / 30)
    await ws.close(code=1008, reason=f"请求过于频繁，请稍后重试！{expires} 秒后重试")
