from typing import Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.auth.schema import LoginSchema, SelectTenantSchema
from app.api.v1.module_system.auth.service import AuthService
from app.api.v1.module_system.user.schema import ProfileUpdateSchema, UserChangePasswordSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema, RefreshTokenPayloadSchema
from app.core.dependencies import db_getter, get_current_user, redis_getter
from app.core.exceptions import CustomException
from app.utils.ip_local_util import get_client_ip

AuthRouter = APIRouter(prefix="/auth", tags=["认证(旧路径兼容)"])
CoreRouter = APIRouter(tags=["核心认证"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


async def _merged(request: Request) -> dict[str, Any]:
    """json + form + query。登录仍兼容三种来源。"""
    body: dict[str, Any] = {}
    try:
        raw = await request.json()
        if isinstance(raw, dict):
            body = raw
    except Exception:
        body = {}
    if not body:
        try:
            form = await request.form()
            body = dict(form)
        except Exception:
            body = {}
    return {**dict(request.query_params), **body}


def _validate(schema: type, raw: dict):
    try:
        return schema.model_validate(raw)
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from e

AuthRouter = APIRouter(prefix="/auth", tags=["认证(旧路径兼容)"])
CoreRouter = APIRouter(tags=["核心认证"])


def _ok(data: Any = None, msg: str = "success") -> SuccessResponse:
    return SuccessResponse(data=data if data is not None else {}, msg=msg)


@CoreRouter.get("/core/captcha")
async def captcha(db: AsyncSession = Depends(db_getter), redis: Redis = Depends(redis_getter)):
    return _ok(await AuthService(db, redis).captcha())


@CoreRouter.post("/core/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(db_getter),
    redis: Redis = Depends(redis_getter),
):
    data = _validate(LoginSchema, await _merged(request))
    try:
        result = await AuthService(db, redis).login(
            data.model_dump(),
            client_ip=get_client_ip(request) or "",
            user_agent=request.headers.get("User-Agent") or "",
        )
        return _ok(result)
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1, status_code=200 if e.code not in (401,) else e.status_code)


@CoreRouter.post("/core/refresh")
async def refresh(request: Request, db: AsyncSession = Depends(db_getter), redis: Redis = Depends(redis_getter)):
    data = _validate(RefreshTokenPayloadSchema, await _merged(request))
    try:
        return _ok(await AuthService(db, redis).refresh(data.refresh_token))
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 401, status_code=401)


@CoreRouter.post("/core/logout")
async def logout(
    request: Request,
    auth: AuthSchema = Depends(get_current_user),
    redis: Redis = Depends(redis_getter),
):
    token = getattr(request.state, "access_token", None) or ""
    if not token:
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    await AuthService(auth.db, redis).logout(token)  # type: ignore[arg-type]
    return _ok({})


@CoreRouter.get("/core/tenants-by-username")
async def tenants_by_username(username: str = "", db: AsyncSession = Depends(db_getter)):
    return _ok(await AuthService(db).tenants_by_username(username))


@CoreRouter.get("/core/user-tenants")
async def user_tenants(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await AuthService(auth.db).tenants_by_username(auth.user.username))  # type: ignore[arg-type]


@CoreRouter.post("/core/switch-tenant")
async def switch_tenant(
    request: Request,
    auth: AuthSchema = Depends(get_current_user),
    redis: Redis = Depends(redis_getter),
):
    data = _validate(SelectTenantSchema, await _merged(request))
    try:
        return _ok(await AuthService(auth.db, redis).switch_tenant(auth, data.tenant_id))  # type: ignore[arg-type]
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@CoreRouter.get("/core/system/user")
async def system_user(auth: AuthSchema = Depends(get_current_user)):
    return _ok(await AuthService(auth.db).current_user_info(auth))  # type: ignore[arg-type]


@CoreRouter.get("/core/system/menu")
async def system_menu(auth: AuthSchema = Depends(get_current_user)):
    from app.api.v1.module_system.menu.service import MenuService

    return _ok(await MenuService(auth).get_user_menu_tree())


@CoreRouter.get("/core/system/permissions")
async def system_permissions(auth: AuthSchema = Depends(get_current_user)):
    from app.api.v1.module_system.menu.service import MenuService

    return _ok(await MenuService(auth).get_user_permissions())


@CoreRouter.get("/core/system/dictAll")
async def system_dict_all(auth: AuthSchema = Depends(get_current_user)):
    from app.api.v1.module_system.dict.service import DictService

    return _ok(await DictService(db=auth.db).get_all_data())  # type: ignore[arg-type]


@CoreRouter.get("/core/system/getUserSelectorList")
async def system_user_selector_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/system/getUserSelectorList（部门领导等 sa-user 下拉）。"""
    from app.api.v1.module_system.user.service import UserService

    return _ok(await UserService(auth).get_selector_list(dict(request.query_params)))


@CoreRouter.get("/core/system/getResourceCategory")
async def system_resource_category(request: Request, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/system/getResourceCategory（选图弹窗分类树）。"""
    from app.api.v1.module_system.attachment.service import AttachmentCategoryService

    return _ok(await AttachmentCategoryService(auth).get_list(dict(request.query_params)))


@CoreRouter.get("/core/system/getResourceList")
async def system_resource_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/system/getResourceList（选图弹窗资源列表）。"""
    from app.api.v1.module_system.attachment.service import AttachmentService

    return _ok(await AttachmentService(auth).get_list(dict(request.query_params)))


@CoreRouter.post("/core/system/uploadImage")
async def system_upload_image(
    file: UploadFile | None = File(None),
    category_id: int = Form(1),
    auth: AuthSchema = Depends(get_current_user),
):
    """对齐 phpserver /api/core/system/uploadImage（选图弹窗 / 头像上传）。"""
    from app.api.v1.module_system.attachment.service import AttachmentService

    if file is None:
        return ErrorResponse(msg="请选择要上传的文件")
    try:
        # 域名走 upload_config.upload_local_domain，避免 root_path=/api 污染 URL
        return _ok(
            await AttachmentService(auth).upload(file, category_id=category_id),
            "上传成功",
        )
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@CoreRouter.post("/core/user/updateInfo")
async def user_update_info(data: ProfileUpdateSchema, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/user/updateInfo（个人中心改资料/头像）。"""
    from app.api.v1.module_system.user.service import UserService

    user_id = int(getattr(auth.user, "id", 0) or 0)
    if not user_id:
        return ErrorResponse(msg="未登录", code=401, status_code=401)
    try:
        return _ok(await UserService(auth).update_profile(user_id, data.model_dump(exclude_unset=True)), "资料修改成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@CoreRouter.post("/core/user/modifyPassword")
async def user_modify_password(data: UserChangePasswordSchema, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/user/modifyPassword（个人中心改密码）。"""
    from app.api.v1.module_system.user.service import UserService

    user_id = int(getattr(auth.user, "id", 0) or 0)
    if not user_id:
        return ErrorResponse(msg="未登录", code=401, status_code=401)
    try:
        await UserService(auth).change_own_password(user_id, data.old_password, data.new_password)
        return _ok({}, "密码修改成功")
    except CustomException as e:
        return ErrorResponse(msg=e.msg, code=e.code or 1)


@CoreRouter.get("/core/system/getLoginLogList")
async def system_login_log_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/system/getLoginLogList（个人中心登录日志）。"""
    from app.api.v1.module_system.logs.service import LogService

    return _ok(await LogService(auth).login_page(dict(request.query_params)))


@CoreRouter.get("/core/system/getOperationLogList")
async def system_operation_log_list(request: Request, auth: AuthSchema = Depends(get_current_user)):
    """对齐 phpserver /api/core/system/getOperationLogList（个人中心操作日志）。"""
    from app.api.v1.module_system.logs.service import LogService

    return _ok(await LogService(auth).oper_page(dict(request.query_params)))


@CoreRouter.get("/core/system/statistics")
async def system_statistics(auth: AuthSchema = Depends(get_current_user)):
    """控制台基础统计：用户/附件/登录/操作数。"""
    return _ok(await AuthService(auth.db).statistics())  # type: ignore[arg-type]


@CoreRouter.get("/core/system/loginChart")
async def system_login_chart(auth: AuthSchema = Depends(get_current_user)):
    """近 30 天每日登录折线图。"""
    return _ok(await AuthService(auth.db).login_chart())  # type: ignore[arg-type]


@CoreRouter.get("/core/system/loginBarChart")
async def system_login_bar_chart(auth: AuthSchema = Depends(get_current_user)):
    """近 12 个月登录柱状图。"""
    return _ok(await AuthService(auth.db).login_bar_chart())  # type: ignore[arg-type]


# 旧路径兼容占位
@AuthRouter.post("/login")
async def legacy_login(request: Request, db: AsyncSession = Depends(db_getter), redis: Redis = Depends(redis_getter)):
    return await login(request, db, redis)
