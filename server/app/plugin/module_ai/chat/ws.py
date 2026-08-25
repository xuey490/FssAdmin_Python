import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import async_db_session
from app.core.dependencies import _authenticate
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.router_class import OperationLogRoute

from .schema import ChatQuerySchema
from .service import ChatService, get_user_model_config

WS_AI = APIRouter(
    route_class=OperationLogRoute,
    prefix="/ai/chat",
    tags=["智能助手WebSocket"],
)


async def _send_error_and_close(websocket: WebSocket, message: str) -> None:
    """发送错误消息并关闭连接"""
    try:
        await websocket.send_text(f"错误: {message}")
    except RuntimeError:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass


@WS_AI.websocket("/ws", name="WebSocket聊天")
async def websocket_chat_controller(websocket: WebSocket) -> None:
    """
    WebSocket 聊天接口。

    支持的消息格式（JSON）：
    - 对话：{"message": "...", "session_id": "...", "files": [...]}
    - 停止：{"action": "stop", "session_id": "..."}

    ws://127.0.0.1:8001/api/v1/ai/chat/ws?token=xxx
    """
    await websocket.accept()
    token = websocket.query_params.get("token")

    if not token:
        await _send_error_and_close(websocket, "未提供认证token，请重新登录")
        return

    # 跨消息循环共享的停止信号：客户端发送 stop 时 set，生成器检测到后退出
    stop_event = asyncio.Event()
    # 标记当前是否在生成中，便于 stop 校验
    is_generating = asyncio.Event()

    try:
        redis = websocket.app.state.redis
        async with async_db_session() as db:
            auth = await _authenticate(token, db, redis)

            user = auth.user
            logger.info("WebSocket连接已建立: {} - 用户: {}", websocket.client, user.username if user else "未认证")

            chat_service = ChatService(auth)

            # 消息循环
            while True:
                try:
                    data = await websocket.receive_text()
                    try:
                        message_data = json.loads(data)
                        query = ChatQuerySchema(**message_data)
                    except json.JSONDecodeError:
                        logger.warning("收到非JSON消息: {}", data)
                        await websocket.send_text("消息格式错误，请发送JSON格式的消息")
                        continue
                    except Exception as e:
                        logger.warning("消息校验失败: {}", e)
                        await websocket.send_text(f"消息格式错误: {e}")
                        continue

                    # 处理停止指令
                    if query.action == "stop":
                        if is_generating.is_set():
                            stop_event.set()
                            logger.info("收到停止指令: session={}", query.session_id)
                            await websocket.send_text("[STOPPED]")
                        else:
                            await websocket.send_text("当前没有正在进行的生成任务")
                        continue

                    # 对话指令
                    logger.info("收到聊天查询: session_id={}", query.session_id)

                    is_generating.set()
                    stop_event.clear()
                    # 读取用户的 AI 模型配置（每次可动态切换）
                    model_config = await get_user_model_config(redis, user.id)
                    try:
                        async for chunk in chat_service.chat_query(
                            query=query,
                            stop_event=stop_event,
                            model_config=model_config,
                        ):
                            if not chunk:
                                continue
                            try:
                                await websocket.send_text(chunk)
                            except RuntimeError:
                                logger.warning("WebSocket连接已关闭，停止发送消息")
                                return
                    finally:
                        is_generating.clear()
                        stop_event.clear()

                    # 告知前端生成结束
                    try:
                        await websocket.send_text("[DONE]")
                    except RuntimeError:
                        return

                except WebSocketDisconnect:
                    logger.info("WebSocket连接已断开: {}", websocket.client)
                    return

    except CustomException as e:
        # 认证失败等业务异常
        logger.warning("WebSocket认证失败: {}", e.msg)
        await _send_error_and_close(websocket, e.msg)
    except Exception as e:
        # 未知异常
        logger.exception("WebSocket未知异常: {}", e)
        await _send_error_and_close(websocket, "服务器内部错误")
