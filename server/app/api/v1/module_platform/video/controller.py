from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .meta_queue import MetaFetchQueue
from .schema import (
    DownloadQueueQueryParam,
    FormatItemSchema,
    JobOutSchema,
    LocalFilesOutSchema,
    PreviewOutSchema,
    ProgressItemSchema,
    VideoCreateSchema,
    VideoDownloadCreateSchema,
    VideoOutSchema,
    VideoQueryParam,
    VideoUpdateSchema,
)
from .service import VideoService

VideoRouter = APIRouter(route_class=OperationLogRoute, prefix="/video", tags=["平台管理", "视频下载"])


def _enqueue_meta(pending: list[tuple[int, bool]]) -> None:
    MetaFetchQueue.instance().enqueue_many(pending)


def _enqueue_meta_one(video_id: int) -> None:
    MetaFetchQueue.instance().enqueue(video_id, enqueue_download=False)

@VideoRouter.get("/list", summary="视频列表", response_model=ResponseSchema[PageResultSchema[VideoOutSchema]])
async def video_list_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[VideoQueryParam, Depends()],
) -> JSONResponse:
    items, total = await VideoService(auth).get_list(
        page_no=page.page_no,
        page_size=page.page_size,
        order_by=page.order_by,
        search=search,
    )
    offset = (page.page_no - 1) * page.page_size
    result = PageResultSchema(
        page_no=page.page_no,
        page_size=page.page_size,
        total=total,
        has_next=offset + page.page_size < total,
        items=items,
    )
    return SuccessResponse(data=result, msg="获取成功")


@VideoRouter.get(
    "/progress",
    summary="下载进度快照",
    response_model=ResponseSchema[list[ProgressItemSchema]],
)
async def video_progress_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
    ids: Annotated[str, Query(description="视频ID，逗号分隔，如 1,2,3")],
) -> JSONResponse:
    video_ids = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    result = await VideoService(auth).progress_snapshot(video_ids)
    return SuccessResponse(data=result, msg="ok")

@VideoRouter.post("/create", summary="批量创建视频链接", response_model=ResponseSchema[list[VideoOutSchema]])
async def video_create_controller(
    data: Annotated[VideoCreateSchema, Body()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:create"]))],
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    result, pending, skipped = await VideoService(auth).create(data)
    # 等请求事务提交后再入队，避免工人读不到新行
    background_tasks.add_task(_enqueue_meta, pending)
    if not result and skipped:
        msg = f"全部链接已存在，已跳过 {skipped} 条"
    elif skipped:
        msg = f"已保存 {len(result)} 条，跳过已存在 {skipped} 条，正在后台获取视频信息"
    else:
        msg = f"已保存 {len(result)} 条，正在后台获取视频信息"
    return SuccessResponse(data=result, msg=msg)


@VideoRouter.put("/update/{id}", summary="更新视频链接", response_model=ResponseSchema[VideoOutSchema])
async def video_update_controller(
    id: Annotated[int, Path(ge=1)],
    data: Annotated[VideoUpdateSchema, Body()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:update"]))],
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    result = await VideoService(auth).update(id, data)
    background_tasks.add_task(_enqueue_meta_one, id)
    return SuccessResponse(data=result, msg="已更新，正在重新获取视频信息")


@VideoRouter.post("/refresh/{id}", summary="重新获取视频信息", response_model=ResponseSchema[VideoOutSchema])
async def video_refresh_controller(
    id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:update"]))],
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    result = await VideoService(auth).refresh(id)
    background_tasks.add_task(_enqueue_meta_one, id)
    return SuccessResponse(data=result, msg="已加入获取队列")


@VideoRouter.delete("/delete/{id}", summary="删除视频", response_model=ResponseSchema[None])
async def video_delete_controller(
    id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:delete"]))],
) -> JSONResponse:
    await VideoService(auth).delete(id)
    return SuccessResponse(msg="删除成功")


@VideoRouter.get("/preview/{id}", summary="预览信息", response_model=ResponseSchema[PreviewOutSchema])
async def video_preview_controller(
    id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
) -> JSONResponse:
    result = await VideoService(auth).preview(id)
    return SuccessResponse(data=result, msg="获取成功")


@VideoRouter.get("/stream/{id}", summary="流式代理播放", response_class=StreamingResponse)
async def video_stream_controller(
    id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
    format_id: Annotated[str | None, Query(description="yt-dlp format_id，空则 bestvideo")] = None,
) -> StreamingResponse:
    return await VideoService(auth).stream(id, format_id=format_id)


@VideoRouter.get("/formats/{id}", summary="可用格式列表", response_model=ResponseSchema[list[FormatItemSchema]])
async def video_formats_controller(
    id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
) -> JSONResponse:
    result = await VideoService(auth).formats(id)
    return SuccessResponse(data=result, msg="获取成功")


@VideoRouter.get(
    "/files/{id}",
    summary="已下载文件列表",
    response_model=ResponseSchema[LocalFilesOutSchema],
)
async def video_local_files_controller(
    id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
) -> JSONResponse:
    result = await VideoService(auth).list_local_files(id)
    return SuccessResponse(data=result, msg="获取成功")


@VideoRouter.post("/download/{id}", summary="创建下载任务", response_model=ResponseSchema[JobOutSchema])
async def video_download_controller(
    id: Annotated[int, Path(ge=1)],
    data: Annotated[VideoDownloadCreateSchema, Body()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:download"]))],
) -> JSONResponse:
    result = await VideoService(auth).enqueue_download(id, data)
    return SuccessResponse(data=result, msg="已加入下载队列")


@VideoRouter.get(
    "/download/queue",
    summary="下载队列列表",
    response_model=ResponseSchema[PageResultSchema[JobOutSchema]],
)
async def download_queue_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[DownloadQueueQueryParam, Depends()],
) -> JSONResponse:
    items, total = await VideoService(auth).queue_list(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
    )
    offset = (page.page_no - 1) * page.page_size
    result = PageResultSchema(
        page_no=page.page_no,
        page_size=page.page_size,
        total=total,
        has_next=offset + page.page_size < total,
        items=items,
    )
    return SuccessResponse(data=result, msg="获取成功")


@VideoRouter.post("/download/job/{job_id}/pause", summary="暂停下载任务", response_model=ResponseSchema[JobOutSchema])
async def download_pause_controller(
    job_id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:download"]))],
) -> JSONResponse:
    result = await VideoService(auth).pause_job(job_id)
    return SuccessResponse(data=result, msg="已暂停")


@VideoRouter.post("/download/job/{job_id}/resume", summary="继续下载任务", response_model=ResponseSchema[JobOutSchema])
async def download_resume_controller(
    job_id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:download"]))],
) -> JSONResponse:
    result = await VideoService(auth).resume_job(job_id)
    return SuccessResponse(data=result, msg="已继续")


@VideoRouter.post("/download/job/{job_id}/stop", summary="停止下载任务", response_model=ResponseSchema[JobOutSchema])
async def download_stop_controller(
    job_id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:download"]))],
) -> JSONResponse:
    result = await VideoService(auth).stop_job(job_id)
    return SuccessResponse(data=result, msg="已停止")


@VideoRouter.post("/download/queue/pause-all", summary="全局暂停队列")
async def download_pause_all_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:download"]))],
) -> JSONResponse:
    n = await VideoService(auth).pause_all()
    return SuccessResponse(data={"count": n}, msg="已全局暂停")


@VideoRouter.post("/download/queue/resume-all", summary="全局继续队列")
async def download_resume_all_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_platform:video:download"]))],
) -> JSONResponse:
    n = await VideoService(auth).resume_all()
    return SuccessResponse(data={"count": n}, msg="已全局继续")
