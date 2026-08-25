"""视频 / 下载任务 CRUD。"""

from typing import Any

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import VideoDownloadModel, VideoModel
from .schema import VideoUpdateSchema


class VideoCRUD(CRUDBase[VideoModel, dict[str, Any], VideoUpdateSchema]):
    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=VideoModel, auth=auth)


class VideoDownloadCRUD(CRUDBase[VideoDownloadModel, dict[str, Any], dict[str, Any]]):
    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=VideoDownloadModel, auth=auth)
