from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.common.constant import DATE_DISPLAY_FMT, DATETIME_DISPLAY_FMT, RET, TIME_DISPLAY_FMT

_JSON_DATETIME_CUSTOM_ENCODER: dict[type[Any], Any] = {
    datetime: lambda d: d.strftime(DATETIME_DISPLAY_FMT),
    date: lambda d: d.strftime(DATE_DISPLAY_FMT),
    time: lambda t: t.strftime(TIME_DISPLAY_FMT),
}


def jsonable_response_content(content: Any) -> Any:
    return jsonable_encoder(content, custom_encoder=_JSON_DATETIME_CUSTOM_ENCODER)


class ResponseSchema[T](BaseModel):
    """对齐 web/phpserver：code=200 成功，同时返回 msg 与 message。"""

    code: int = Field(default=200, description="业务状态码")
    msg: str = Field(default="success", description="响应消息")
    message: str = Field(default="success", description="响应消息(兼容)")
    data: T | None = Field(default=None, description="响应数据")
    status_code: int = Field(default=status.HTTP_200_OK, description="HTTP状态码")
    success: bool = Field(default=True, description="操作是否成功")


class SuccessResponse(JSONResponse):
    def __init__(
        self,
        data: Any | None = None,
        msg: str = "success",
        code: int = 200,
        status_code: int = status.HTTP_200_OK,
        success: bool = True,
        message: str | None = None,
    ) -> None:
        content = ResponseSchema(
            code=code,
            msg=msg,
            message=message if message is not None else msg,
            data=data,
            status_code=status_code,
            success=success,
        ).model_dump()
        super().__init__(content=jsonable_response_content(content), status_code=status_code)
        self.headers["Content-Type"] = "application/json; charset=utf-8"


class ErrorResponse(JSONResponse):
    def __init__(
        self,
        data: Any = None,
        msg: str = RET.ERROR.msg,
        code: int = RET.ERROR.code,
        status_code: int = status.HTTP_200_OK,
        success: bool = False,
        message: str | None = None,
    ) -> None:
        content = ResponseSchema(
            code=code,
            msg=msg,
            message=message if message is not None else msg,
            data=data if data is not None else {},
            status_code=status_code,
            success=success,
        ).model_dump()
        # phpserver 业务失败多为 HTTP 200 + 非 200 code；鉴权失败仍可用 401
        super().__init__(content=jsonable_response_content(content), status_code=status_code)
        self.headers["Content-Type"] = "application/json; charset=utf-8"


class StreamResponse(StreamingResponse):
    def __init__(
        self,
        data: Any = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(
            content=data,
            status_code=status_code,
            media_type=media_type,
            headers=headers,
            background=background,
        )


class UploadFileResponse(FileResponse):
    def __init__(
        self,
        file_path: str,
        filename: str,
        media_type: str = "application/octet-stream",
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        status_code: int = 200,
    ) -> None:
        super().__init__(
            path=file_path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            filename=filename,
            stat_result=None,
            method=None,
            content_disposition_type="attachment",
        )


def page_result(
    rows: list[Any],
    total: int,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """web 表格可识别 list/data + page/current_page + limit/per_page/size。"""
    return {
        "list": rows,
        "data": rows,
        "total": total,
        "page": page,
        "current_page": page,
        "limit": limit,
        "per_page": limit,
        "size": limit,
    }
