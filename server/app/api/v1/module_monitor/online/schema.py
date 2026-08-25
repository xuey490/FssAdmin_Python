"""在线用户 — 对齐 web `safeguard/online` / server1 OnlineService 字段。"""

from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class OnlineOutSchema(BaseModel):
    """前端表格行（camelCase）。"""

    model_config = ConfigDict(populate_by_name=True)

    tokenId: str = Field(..., description="会话编号")
    userName: str = Field(default="", description="登录账号")
    deptName: str = Field(default="", description="所属部门")
    ipaddr: str = Field(default="", description="主机")
    loginLocation: str = Field(default="", description="登录地点")
    os: str = Field(default="", description="操作系统")
    browser: str = Field(default="", description="浏览器")
    loginTime: str = Field(default="", description="登录时间")


@dataclass
class OnlineQueryParam:
    """列表查询参数（对齐 web searchForm + useTable page/limit）。"""

    def __init__(
        self,
        ipaddr: str | None = Query(None, description="登录地址"),
        userName: str | None = Query(None, description="用户账号"),
        username: str | None = Query(None, description="用户账号(兼容)"),
        orderField: str | None = Query("loginTime", description="排序字段"),
        orderType: str | None = Query("desc", description="排序方向 asc|desc"),
        page: int = Query(1, ge=1, description="页码"),
        limit: int = Query(10, ge=1, le=200, description="每页条数"),
        pageNum: int | None = Query(None, description="页码兼容"),
        pageSize: int | None = Query(None, description="每页兼容"),
        current: int | None = Query(None, description="页码兼容"),
        size: int | None = Query(None, description="每页兼容"),
    ) -> None:
        self.ipaddr = (ipaddr or "").strip()
        self.user_name = (userName or username or "").strip()
        self.order_field = (orderField or "loginTime").strip()
        self.order_type = (orderType or "desc").strip().lower()
        self.page = int(pageNum or current or page or 1)
        self.limit = int(pageSize or size or limit or 10)
