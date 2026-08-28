import re
from datetime import date, datetime, time
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import AfterValidator, PlainSerializer, WithJsonSchema

from app.common.constant import DATE_DISPLAY_FMT, DATETIME_DISPLAY_FMT, TIME_DISPLAY_FMT

# 自定义日期时间字符串类型
DateTimeStr = Annotated[
    datetime,
    AfterValidator(lambda x: datetime_validator(x)),
    PlainSerializer(
        lambda x: x.strftime(DATETIME_DISPLAY_FMT) if isinstance(x, datetime) else str(x),
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

# 自定义日期字符串类型
DateStr = Annotated[
    date,
    AfterValidator(lambda x: date_validator(x)),
    PlainSerializer(
        lambda x: x.strftime(DATE_DISPLAY_FMT) if isinstance(x, date) else str(x),
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

# 自定义时间字符串类型
TimeStr = Annotated[
    time,
    AfterValidator(lambda x: time_validator(x)),
    PlainSerializer(
        lambda x: x.strftime(TIME_DISPLAY_FMT) if isinstance(x, time) else str(x),
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

# 自定义手机号类型
Telephone = Annotated[
    str,
    AfterValidator(lambda x: mobile_validator(x)),
    PlainSerializer(lambda x: x, return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

# 自定义邮箱类型
Email = Annotated[
    str,
    AfterValidator(lambda x: email_validator(x)),
    PlainSerializer(lambda x: x, return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


def datetime_validator(value: str | datetime) -> datetime:
    """
    日期格式验证器。

    参数:
    - value (str | datetime): 日期值。

    返回:
    - datetime: 格式化后的日期。

    异常:
    - CustomException: 日期格式无效时抛出。
    """
    try:
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_DISPLAY_FMT)
        if isinstance(value, datetime):
            return value
    except Exception:
        pass
    raise ValueError("无效的日期格式")


def date_validator(value: str | date) -> date:
    """
    日期格式验证器。

    参数:
    - value (str | date): 日期值。

    返回:
    - date: 格式化后的日期。

    异常:
    - CustomException: 日期格式无效时抛出。
    """
    try:
        if isinstance(value, str):
            return datetime.strptime(value, DATE_DISPLAY_FMT).date()
        if isinstance(value, date):
            return value
    except Exception:
        pass
    raise ValueError("无效的日期格式")


def time_validator(value: str | time) -> time:
    """
    时间格式验证器。

    参数:
    - value (str | time): 时间值。

    返回:
    - time: 格式化后的时间。

    异常:
    - CustomException: 时间格式无效时抛出。
    """
    try:
        if isinstance(value, str):
            return datetime.strptime(value, TIME_DISPLAY_FMT).time()
        if isinstance(value, time):
            return value
    except Exception:
        pass
    raise ValueError("无效的时间格式")


def email_validator(value: str) -> str:
    """
    邮箱地址验证器。

    参数:
    - value (str): 邮箱地址。

    返回:
    - str: 验证后的邮箱地址。

    异常:
    - ValueError: 邮箱格式无效时抛出。
    """
    if not value:
        raise ValueError("邮箱地址不能为空")

    regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(regex, value):
        raise ValueError("邮箱地址格式不正确")

    return value


def mobile_validator(value: str | None) -> str | None:
    """
    手机号验证器。

    参数:
    - value (str | None): 手机号。

    返回:
    - str | None: 验证后的手机号。

    异常:
    - ValueError: 手机号格式无效时抛出。
    """
    if not value:
        return value

    if len(value) != 11 or not value.isdigit():
        raise ValueError("手机号格式不正确")

    regex = r"^1(3\d|4[4-9]|5[0-35-9]|6[67]|7[013-8]|8[0-9]|9[0-9])\d{8}$"

    if not re.match(regex, value):
        raise ValueError("手机号格式不正确")

    return value


def phone_validator(value: str | None) -> str | None:
    """可选电话：11 位手机号走 mobile_validator，其它号码只限长度。"""
    if not value or not str(value).strip():
        return None
    v = str(value).strip()
    if len(v) == 11 and v.isdigit():
        return mobile_validator(v)
    if len(v) > 20:
        raise ValueError("联系电话长度不能超过 20")
    return v


def username_validator(value: str) -> str:
    """账号：字母开头，3–32 位，仅字母/数字/_ . -。"""
    v = (value or "").strip()
    if not v:
        raise ValueError("账号不能为空")
    if not re.match(r"^[A-Za-z][A-Za-z0-9_.-]{2,31}$", v):
        raise ValueError("账号需以字母开头，3-32 位，仅允许字母、数字、_ . -")
    return v


def password_validator(value: str | None, *, required: bool = False) -> str | None:
    """密码：6–128 位；required=False 时空值跳过。"""
    if not value:
        if required:
            raise ValueError("密码不能为空")
        return value
    if len(value) < 6:
        raise ValueError("密码长度不能少于 6 位")
    if len(value) > 128:
        raise ValueError("密码长度不能超过 128 位")
    return value


def avatar_validator(value: str | None) -> str | None:
    """头像：相对路径或 http(s) URL。"""
    if not value:
        return value
    v = value.strip()
    if v.startswith("/") or v.startswith("uploads") or v.startswith("."):
        return v
    parsed = urlparse(v)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return v
    raise ValueError("头像地址需为有效路径或 HTTP/HTTPS URL")


def validate_required_code(value: str | None) -> str:
    """
    必填编码校验：字母开头，总长 2–64，仅含字母/数字/下划线。

    参数:
    - value (str | None): 编码。

    返回:
    - str: 去空白后的编码。

    异常:
    - ValueError: 为空或格式不合法。
    """
    if value is None or not str(value).strip():
        raise ValueError("编码不能为空")
    v = value.strip()
    if len(v) < 2 or len(v) > 64:
        raise ValueError("编码长度需在 2-64 个字符之间")
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", v):
        raise ValueError("编码需以字母开头，仅允许字母、数字、下划线")
    return v


def code_validator(value: str | None) -> str | None:
    """
    可选编码验证器（为空则跳过）。

    参数:
    - value (str | None): 编码。

    返回:
    - str | None: 验证后的编码；未填写时返回 None。

    异常:
    - CustomException: 已填写但格式无效时抛出。
    """
    if not value:
        return value
    v = value.strip()
    if not v:
        return None
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]{1,15}$", v):
        raise ValueError("编码需字母开头，允许字母/数字/下划线，长度2-16")
    return v


def menu_request_validator(data: Any) -> Any:
    """菜单提交校验（字段对齐 sa_system_menu：type/path/component/link_url）。"""
    menu_types = {1: "目录", 2: "菜单", 3: "按钮", 4: "外链"}

    if data.type not in menu_types:
        raise ValueError(f"菜单类型必须为: {','.join(map(str, menu_types.keys()))}")

    if data.type == 2 and not (getattr(data, "path", None) or "").strip():
        raise ValueError("菜单类型必须填写路由路径")
    if data.type == 2 and not (getattr(data, "component", None) or "").strip():
        raise ValueError("菜单类型必须填写组件路径")
    if data.type == 4 and not (getattr(data, "link_url", None) or "").strip():
        raise ValueError("外链类型必须填写链接地址")

    return data


def role_permission_request_validator(data: Any) -> Any:
    """角色权限设置数据验证器。"""
    data_scopes = {
        1: "仅本人数据权限",
        2: "本部门数据权限",
        3: "本部门及以下数据权限",
        4: "全部数据权限",
        5: "自定义数据权限",
    }

    if data.data_scope not in data_scopes:
        raise ValueError(f"数据权限范围必须为: {','.join(map(str, data_scopes.keys()))}")

    if not data.role_ids:
        raise ValueError("角色不能为空")

    return data
