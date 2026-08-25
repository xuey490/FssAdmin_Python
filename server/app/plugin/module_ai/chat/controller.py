from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, redis_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    AiChatRequestSchema,
    AiChatResponseSchema,
    AiModelConfigListResponse,
    AiModelConfigSchema,
    AiModelConfigUpdateSchema,
    ChatSessionCreateSchema,
    ChatSessionQueryParam,
    ChatSessionUpdateSchema,
)
from .service import AiModelConfigService, ChatService

ChatRouter = APIRouter(route_class=OperationLogRoute, prefix="/chat", tags=["AI管理", "AI对话"])


@ChatRouter.get(
    "/detail/{session_id}",
    summary="获取会话详情",
    response_model=ResponseSchema[dict[str, Any]],
)
async def get_session_detail_controller(
    session_id: Annotated[str, Path(description="会话ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:detail"]))],
) -> JSONResponse:
    service = ChatService(auth)
    result = await service.get_session(session_id=session_id)
    return SuccessResponse(data=result, msg="获取会话详情成功")


@ChatRouter.get(
    "/list",
    summary="查询会话列表",
    response_model=ResponseSchema[dict],
)
async def get_session_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ChatSessionQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    service = ChatService(auth)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询会话列表成功")


@ChatRouter.post(
    "/create",
    summary="创建会话",
    response_model=ResponseSchema[dict[str, Any]],
)
async def create_session_controller(
    data: ChatSessionCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:create"]))],
) -> JSONResponse:
    service = ChatService(auth)
    result = await service.create(data=data)
    return SuccessResponse(data=result, msg="创建会话成功")


@ChatRouter.put(
    "/update/{session_id}",
    summary="更新会话",
    response_model=ResponseSchema[None],
)
async def update_session_controller(
    session_id: Annotated[str, Path(description="会话ID")],
    data: ChatSessionUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:update"]))],
) -> JSONResponse:
    service = ChatService(auth)
    await service.update(session_id=session_id, data=data)
    return SuccessResponse(data=None, msg="更新会话成功")


@ChatRouter.delete(
    "/delete",
    summary="删除会话",
    response_model=ResponseSchema[None],
)
async def delete_session_controller(
    session_ids: list[str],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:delete"]))],
) -> JSONResponse:
    service = ChatService(auth)
    await service.delete(session_ids=session_ids)
    return SuccessResponse(data=None, msg="删除会话成功")


@ChatRouter.post(
    "/ai-chat",
    summary="AI 对话（非流式）",
    response_model=ResponseSchema[AiChatResponseSchema],
)
async def ai_chat_controller(
    data: AiChatRequestSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    service = ChatService(auth)
    result = await service.chat_non_stream(
        message=data.message,
        session_id=data.session_id,
    )
    return SuccessResponse(
        data=AiChatResponseSchema(
            response=result["response"],
            session_id=result["session_id"],
            function_calls=result.get("function_calls"),
            action=result.get("action"),
        ),
        msg="对话成功",
    )


# ============ AI 模型配置 ============ #


@ChatRouter.get(
    "/model",
    summary="获取当前用户的 AI 模型配置列表（含当前激活 ID）",
    response_model=ResponseSchema[AiModelConfigListResponse],
)
async def list_model_config_controller(
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    result = await service.list()
    return SuccessResponse(data=result, msg="获取模型配置列表成功")


@ChatRouter.post(
    "/model",
    summary="新增一个 AI 模型配置",
    response_model=ResponseSchema[dict[str, Any]],
)
async def create_model_config_controller(
    data: AiModelConfigUpdateSchema,
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:update"]))],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    payload = AiModelConfigSchema(**data.model_dump())
    result = await service.create(payload)
    return SuccessResponse(data=result, msg="模型配置已新增")


@ChatRouter.put(
    "/model/{config_id}",
    summary="更新指定 ID 的 AI 模型配置",
    response_model=ResponseSchema[dict[str, Any]],
)
async def update_model_config_controller(
    config_id: Annotated[str, Path(description="配置项 ID")],
    data: AiModelConfigUpdateSchema,
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:update"]))],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    payload = AiModelConfigSchema(**data.model_dump())
    result = await service.update(config_id, payload)
    return SuccessResponse(data=result, msg="模型配置已更新")


@ChatRouter.delete(
    "/model/{config_id}",
    summary="删除指定 ID 的 AI 模型配置",
    response_model=ResponseSchema[None],
)
async def delete_model_config_controller(
    config_id: Annotated[str, Path(description="配置项 ID")],
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:update"]))],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    await service.delete(config_id)
    return SuccessResponse(data=None, msg="模型配置已删除")


@ChatRouter.post(
    "/model/{config_id}/activate",
    summary="切换当前激活的 AI 模型配置（空 ID 表示使用系统默认）",
    response_model=ResponseSchema[None],
)
async def activate_model_config_controller(
    config_id: Annotated[str, Path(description="配置项 ID；传 __default__ 使用系统默认")],
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:chat:update"]))],
) -> JSONResponse:
    service = AiModelConfigService(auth, redis)
    await service.set_active(config_id)
    return SuccessResponse(data=None, msg="已切换模型")
