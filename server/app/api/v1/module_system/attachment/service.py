"""附件服务（本地存储，对齐 phpserver SysAttachmentService）。"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, select

from app.api.v1.module_system.attachment.model import AttachmentCategoryModel, AttachmentModel
from app.api.v1.module_system.common import build_tree, not_deleted, parse_page, row_to_dict
from app.api.v1.module_system.config.model import ConfigModel
from app.common.response import page_result
from app.config.path_conf import BASE_DIR
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.utils.common_util import bytes2human


def _upload_root() -> Path:
    root = BASE_DIR / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def normalize_attachment_url(url: str | None) -> str:
    """去掉误拼的 root_path（/api/uploads → /uploads）。"""
    if not url:
        return ""
    return url.replace("/api/uploads/", "/uploads/")


def strip_api_suffix(domain: str) -> str:
    d = (domain or "").rstrip("/")
    if d.endswith("/api"):
        d = d[:-4]
    return d.rstrip("/")


class AttachmentService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db = auth.db  # type: ignore[assignment]

    def _operator(self) -> int:
        return int(self.auth.user.id) if self.auth.user else 0

    async def _upload_config(self) -> dict[str, str]:
        rows = (
            await self.db.execute(
                select(ConfigModel).where(ConfigModel.group_id == 2, not_deleted(ConfigModel))
            )
        ).scalars().all()
        return {str(r.key): (r.value or "") for r in rows if r.key}

    def _serialize_row(self, row: AttachmentModel) -> dict[str, Any]:
        d = row_to_dict(row)
        d["url"] = normalize_attachment_url(d.get("url"))
        # 字典 upload_mode 的 value 是字符串，统一成 str 便于 SaDict 匹配
        if d.get("storage_mode") is not None:
            d["storage_mode"] = str(d["storage_mode"])
        return d

    async def get_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(AttachmentModel).where(not_deleted(AttachmentModel))
        if params.get("category_id") not in (None, ""):
            q = q.where(AttachmentModel.category_id == int(params["category_id"]))
        if params.get("origin_name"):
            q = q.where(AttachmentModel.origin_name.like(f"%{params['origin_name']}%"))
        if params.get("mime_type"):
            q = q.where(AttachmentModel.mime_type.like(f"{params['mime_type']}%"))
        if params.get("file_ext") or params.get("suffix"):
            ext = str(params.get("file_ext") or params.get("suffix") or "").lstrip(".").lower()
            if ext:
                q = q.where(AttachmentModel.suffix == ext)
        if params.get("storage_mode") not in (None, ""):
            q = q.where(AttachmentModel.storage_mode == int(params["storage_mode"]))
        order_field = params.get("orderField") or "create_time"
        order_type = (params.get("orderType") or "desc").lower()
        col = getattr(AttachmentModel, order_field, AttachmentModel.create_time)
        q = q.order_by(col.asc() if order_type == "asc" else col.desc())
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (await self.db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
        return page_result([self._serialize_row(r) for r in rows], total, page, limit)

    async def get_detail(self, attach_id: int) -> dict[str, Any] | None:
        obj = await self.db.get(AttachmentModel, attach_id)
        if not obj or obj.delete_time:
            return None
        return self._serialize_row(obj)

    async def upload(self, file: UploadFile | None, category_id: int = 1, base_url: str = "") -> dict[str, Any]:
        if file is None:
            raise CustomException(msg="请选择要上传的文件", code=1)
        cfg = await self._upload_config()
        # 对齐 phpserver：存储模式取自 upload_config.upload_mode
        storage_mode = int(cfg.get("upload_mode") or 1)
        domain = strip_api_suffix(base_url or cfg.get("upload_local_domain") or "")

        content = await file.read()
        origin = file.filename or "file"
        suffix = Path(origin).suffix.lstrip(".").lower()
        digest = hashlib.md5(content).hexdigest()
        object_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:16]}.{suffix}" if suffix else f"{uuid.uuid4().hex}"
        day = datetime.now().strftime("%Y/%m/%d")
        rel_dir = f"uploads/{day}"
        abs_dir = _upload_root() / day
        abs_dir.mkdir(parents=True, exist_ok=True)
        abs_path = abs_dir / object_name
        abs_path.write_bytes(content)
        storage_path = f"{rel_dir}/{object_name}"
        url = f"{domain}/{storage_path}" if domain else f"/{storage_path}"
        op = self._operator()
        obj = AttachmentModel(
            category_id=category_id or 1,
            storage_mode=storage_mode,
            origin_name=origin,
            object_name=object_name,
            hash=digest,
            mime_type=file.content_type or "",
            storage_path=storage_path,
            suffix=suffix,
            size_byte=len(content),
            size_info=bytes2human(len(content)),
            url=url,
            created_by=op,
            updated_by=op,
        )
        self.db.add(obj)
        await self.db.flush()
        return self._serialize_row(obj)

    async def update_name(self, attach_id: int, origin_name: str) -> None:
        obj = await self.db.get(AttachmentModel, attach_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="附件不存在", code=404)
        obj.origin_name = origin_name
        obj.updated_by = self._operator()
        await self.db.flush()

    async def delete(self, attach_id: int) -> None:
        obj = await self.db.get(AttachmentModel, attach_id)
        if not obj or obj.delete_time:
            return
        if obj.storage_path:
            physical = BASE_DIR / str(obj.storage_path).lstrip("/")
            if physical.is_file():
                physical.unlink(missing_ok=True)
        obj.delete_time = datetime.now()
        await self.db.flush()

    async def batch_delete(self, ids: list[int]) -> int:
        count = 0
        for aid in ids:
            before = await self.db.get(AttachmentModel, aid)
            if before and not before.delete_time:
                await self.delete(aid)
                count += 1
        return count

    async def move(self, ids: list[int], category_id: int) -> int:
        count = 0
        op = self._operator()
        for aid in ids:
            obj = await self.db.get(AttachmentModel, aid)
            if obj and not obj.delete_time:
                obj.category_id = category_id
                obj.updated_by = op
                count += 1
        await self.db.flush()
        return count

    async def stats(self) -> dict[str, Any]:
        total_size = int(
            (
                await self.db.execute(
                    select(func.coalesce(func.sum(AttachmentModel.size_byte), 0)).where(not_deleted(AttachmentModel))
                )
            ).scalar()
            or 0
        )
        total_count = int(
            (await self.db.execute(select(func.count()).select_from(AttachmentModel).where(not_deleted(AttachmentModel)))).scalar()
            or 0
        )
        type_rows = (
            await self.db.execute(
                select(
                    AttachmentModel.suffix,
                    func.count().label("count"),
                    func.coalesce(func.sum(AttachmentModel.size_byte), 0).label("size"),
                )
                .where(not_deleted(AttachmentModel))
                .group_by(AttachmentModel.suffix)
                .order_by(func.count().desc())
            )
        ).all()
        return {
            "total_size": total_size,
            "total_count": total_count,
            "formatted_size": bytes2human(total_size),
            "type_stats": [{"suffix": r[0], "count": int(r[1]), "size": int(r[2])} for r in type_rows],
        }

    def resolve_path(self, storage_path: str) -> Path:
        return BASE_DIR / storage_path.lstrip("/")


class AttachmentCategoryService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        self.db = auth.db  # type: ignore[assignment]

    def _operator(self) -> int:
        return int(self.auth.user.id) if self.auth.user else 0

    async def _ensure_root(self) -> None:
        """web 约定 id=1 为「全部分类」根节点；缺失或软删时补回。"""
        root = await self.db.get(AttachmentCategoryModel, 1)
        if root is None:
            self.db.add(
                AttachmentCategoryModel(
                    id=1,
                    parent_id=0,
                    level="0,",
                    category_name="全部分类",
                    sort=100,
                    status=1,
                    created_by=1,
                    updated_by=1,
                )
            )
            await self.db.flush()
            return
        if root.delete_time is not None:
            root.delete_time = None
            root.parent_id = 0
            root.category_name = root.category_name or "全部分类"
            root.status = 1
            await self.db.flush()

    @staticmethod
    def _is_tree(params: dict[str, Any]) -> bool:
        v = params.get("tree")
        return v in (True, 1, "1", "true", "True", "yes")

    @staticmethod
    def _to_tree_nodes(rows: list[AttachmentCategoryModel]) -> list[dict[str, Any]]:
        # 对齐 phpserver SysAttachmentCategory::buildTree / web el-tree
        items: list[dict[str, Any]] = []
        for r in rows:
            items.append(
                {
                    "id": int(r.id),
                    "parent_id": int(r.parent_id or 0),
                    "level": r.level,
                    "category_name": r.category_name or "",
                    "sort": r.sort,
                    "status": r.status,
                    "remark": r.remark or "",
                    "label": r.category_name or "",
                    "value": int(r.id),
                    "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else None,
                    "update_time": r.update_time.strftime("%Y-%m-%d %H:%M:%S") if r.update_time else None,
                }
            )
        # promote_orphans：父节点缺失时挂到根，避免左侧「暂无数据」
        return build_tree(items, parent_id=0, promote_orphans=True)

    async def get_list(self, params: dict[str, Any]) -> Any:
        await self._ensure_root()
        q = select(AttachmentCategoryModel).where(not_deleted(AttachmentCategoryModel))
        if params.get("category_name"):
            q = q.where(AttachmentCategoryModel.category_name.like(f"%{params['category_name']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(AttachmentCategoryModel.status == int(params["status"]))
        rows = list(
            (
                await self.db.execute(
                    q.order_by(AttachmentCategoryModel.sort.asc(), AttachmentCategoryModel.id.asc())
                )
            ).scalars().all()
        )
        if self._is_tree(params):
            return self._to_tree_nodes(rows)
        items = []
        for r in rows:
            d = row_to_dict(r)
            d["label"] = r.category_name
            d["value"] = r.id
            items.append(d)
        return page_result(items, len(items), 1, len(items) or 20)

    async def get_detail(self, cat_id: int) -> dict[str, Any] | None:
        obj = await self.db.get(AttachmentCategoryModel, cat_id)
        if not obj or obj.delete_time:
            return None
        return row_to_dict(obj)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        name = (data.get("category_name") or "").strip()
        if not name:
            raise CustomException(msg="分类名称不能为空", code=1)
        parent_id = int(data.get("parent_id") or 0)
        level = "0,"
        if parent_id:
            parent = await self.db.get(AttachmentCategoryModel, parent_id)
            if parent:
                level = f"{parent.level or '0,'}{parent.id},"
        op = self._operator()
        obj = AttachmentCategoryModel(
            parent_id=parent_id,
            level=level,
            category_name=name,
            sort=int(data.get("sort") or 100),
            status=int(data.get("status") if data.get("status") not in (None, "") else 1),
            remark=data.get("remark"),
            created_by=op,
            updated_by=op,
        )
        self.db.add(obj)
        await self.db.flush()
        return {"id": obj.id}

    async def update(self, cat_id: int, data: dict[str, Any]) -> None:
        obj = await self.db.get(AttachmentCategoryModel, cat_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="分类不存在", code=1)
        for field in ("parent_id", "category_name", "sort", "status", "remark"):
            if field in data:
                setattr(obj, field, data[field])
        obj.updated_by = self._operator()
        await self.db.flush()

    async def delete(self, cat_id: int) -> None:
        obj = await self.db.get(AttachmentCategoryModel, cat_id)
        if obj and not obj.delete_time:
            obj.delete_time = datetime.now()
            await self.db.flush()
