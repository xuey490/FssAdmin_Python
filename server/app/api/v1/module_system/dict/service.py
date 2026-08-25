"""字典服务：dictAll + type/data CRUD（对齐 phpserver SysDictService）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.common import not_deleted, parse_page, row_to_dict, status_text
from app.api.v1.module_system.dict.model import DictDataModel, DictTypeModel
from app.common.response import page_result
from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException


class DictService:
    def __init__(self, auth: AuthSchema | None = None, db: AsyncSession | None = None) -> None:
        self.auth = auth
        self.db: AsyncSession = (auth.db if auth else db)  # type: ignore[assignment]

    def _operator(self) -> int:
        if self.auth and self.auth.user:
            return int(self.auth.user.id)
        return 0

    async def ensure_upload_mode_dict(self) -> None:
        """附件列表 SaDict(upload_mode) 依赖此字典；缺失时按 fssoa 种子补齐。"""
        dt = (
            await self.db.execute(
                select(DictTypeModel).where(DictTypeModel.code == "upload_mode")
            )
        ).scalar_one_or_none()
        if dt is None:
            dt = DictTypeModel(
                name="存储模式",
                code="upload_mode",
                status=1,
                remark="上传文件存储模式",
                created_by=1,
                updated_by=1,
            )
            self.db.add(dt)
            await self.db.flush()
        elif dt.delete_time is not None or int(dt.status or 0) != 1:
            dt.delete_time = None
            dt.status = 1
            await self.db.flush()

        defaults = (
            ("本地存储", "1", "#60c041", 100),
            ("阿里云OSS", "2", "#f9901f", 98),
            ("七牛云", "3", "#00ced1", 97),
            ("腾讯云COS", "4", "#1d84ff", 96),
            ("亚马逊S3", "5", "#b48df3", 95),
        )
        rows = (
            await self.db.execute(
                select(DictDataModel).where(DictDataModel.code == "upload_mode")
            )
        ).scalars().all()
        by_val = {str(r.value): r for r in rows}
        for label, value, color, sort in defaults:
            row = by_val.get(value)
            if row is None:
                self.db.add(
                    DictDataModel(
                        type_id=dt.id,
                        label=label,
                        value=value,
                        color=color,
                        code="upload_mode",
                        sort=sort,
                        status=1,
                        created_by=1,
                        updated_by=1,
                    )
                )
            else:
                row.type_id = dt.id
                row.label = row.label or label
                row.color = row.color or color
                row.status = 1
                row.delete_time = None
                row.sort = sort
        await self.db.flush()

    async def get_all_data(self) -> dict[str, list[dict[str, Any]]]:
        await self.ensure_upload_mode_dict()
        types = (
            await self.db.execute(
                select(DictTypeModel).where(DictTypeModel.status == 1, not_deleted(DictTypeModel))
            )
        ).scalars().all()
        result: dict[str, list[dict[str, Any]]] = {}
        for dt in types:
            if not dt.code:
                continue
            rows = (
                await self.db.execute(
                    select(DictDataModel)
                    .where(
                        DictDataModel.type_id == dt.id,
                        DictDataModel.status == 1,
                        not_deleted(DictDataModel),
                    )
                    .order_by(DictDataModel.sort.asc(), DictDataModel.id.asc())
                )
            ).scalars().all()
            result[dt.code] = [
                {
                    "id": r.id,
                    "label": r.label or "",
                    "value": r.value if r.value is not None else "",
                    "color": r.color or "",
                    "disabled": int(r.status or 0) != 1,
                }
                for r in rows
            ]
        return result

    # ── type ──

    async def type_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(DictTypeModel).where(not_deleted(DictTypeModel))
        if params.get("name"):
            q = q.where(DictTypeModel.name.like(f"%{params['name']}%"))
        if params.get("code"):
            q = q.where(DictTypeModel.code.like(f"%{params['code']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(DictTypeModel.status == int(params["status"]))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (
            await self.db.execute(q.order_by(DictTypeModel.id.desc()).offset((page - 1) * limit).limit(limit))
        ).scalars().all()
        items = []
        for r in rows:
            d = row_to_dict(r)
            d["status_text"] = status_text(r.status)
            items.append(d)
        return page_result(items, total, page, limit)

    async def type_detail(self, type_id: int) -> dict[str, Any] | None:
        obj = await self.db.get(DictTypeModel, type_id)
        if not obj or obj.delete_time:
            return None
        return row_to_dict(obj)

    async def type_create(self, data: dict[str, Any]) -> dict[str, Any]:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip()
        if not name or not code:
            raise CustomException(msg="字典名称和编码不能为空", code=1)
        op = self._operator()
        obj = DictTypeModel(
            name=name,
            code=code,
            status=int(data.get("status") if data.get("status") not in (None, "") else 1),
            remark=data.get("remark"),
            created_by=op,
            updated_by=op,
        )
        self.db.add(obj)
        await self.db.flush()
        return {"id": obj.id}

    async def type_update(self, type_id: int, data: dict[str, Any]) -> None:
        obj = await self.db.get(DictTypeModel, type_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="字典类型不存在", code=1)
        for field in ("name", "code", "remark"):
            if field in data:
                setattr(obj, field, data[field])
        if data.get("status") not in (None, ""):
            obj.status = int(data["status"])
        obj.updated_by = self._operator()
        await self.db.flush()

    async def type_delete(self, type_id: int) -> None:
        obj = await self.db.get(DictTypeModel, type_id)
        if not obj or obj.delete_time:
            return
        now = datetime.now()
        obj.delete_time = now
        datas = (
            await self.db.execute(
                select(DictDataModel).where(DictDataModel.type_id == type_id, not_deleted(DictDataModel))
            )
        ).scalars().all()
        for d in datas:
            d.delete_time = now
        await self.db.flush()

    async def type_status(self, type_id: int, status: int) -> None:
        obj = await self.db.get(DictTypeModel, type_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="字典类型不存在", code=1)
        obj.status = status
        obj.updated_by = self._operator()
        await self.db.flush()

    # ── data ──

    async def data_list(self, params: dict[str, Any]) -> dict[str, Any]:
        page, limit = parse_page(params)
        q = select(DictDataModel).where(not_deleted(DictDataModel))
        if params.get("type_id") not in (None, ""):
            q = q.where(DictDataModel.type_id == int(params["type_id"]))
        if params.get("label"):
            q = q.where(DictDataModel.label.like(f"%{params['label']}%"))
        if params.get("value"):
            q = q.where(DictDataModel.value.like(f"%{params['value']}%"))
        if params.get("status") not in (None, ""):
            q = q.where(DictDataModel.status == int(params["status"]))
        total = int((await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0)
        rows = (
            await self.db.execute(
                q.order_by(DictDataModel.sort.asc(), DictDataModel.id.asc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).scalars().all()
        items = []
        for r in rows:
            d = row_to_dict(r)
            d["status_text"] = status_text(r.status)
            items.append(d)
        return page_result(items, total, page, limit)

    async def data_by_code(self, dict_code: str) -> list[dict[str, Any]]:
        dt = (
            await self.db.execute(
                select(DictTypeModel).where(
                    DictTypeModel.code == dict_code,
                    DictTypeModel.status == 1,
                    not_deleted(DictTypeModel),
                )
            )
        ).scalar_one_or_none()
        if not dt:
            return []
        rows = (
            await self.db.execute(
                select(DictDataModel)
                .where(DictDataModel.type_id == dt.id, DictDataModel.status == 1, not_deleted(DictDataModel))
                .order_by(DictDataModel.sort.asc(), DictDataModel.id.asc())
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "label": r.label or "",
                "value": r.value if r.value is not None else "",
                "color": r.color or "",
                "disabled": False,
            }
            for r in rows
        ]

    async def data_detail(self, data_id: int) -> dict[str, Any] | None:
        obj = await self.db.get(DictDataModel, data_id)
        if not obj or obj.delete_time:
            return None
        return row_to_dict(obj)

    async def data_create(self, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("type_id") in (None, ""):
            raise CustomException(msg="字典类型不能为空", code=1)
        op = self._operator()
        obj = DictDataModel(
            type_id=int(data["type_id"]),
            label=data.get("label"),
            value=data.get("value"),
            color=data.get("color"),
            code=data.get("code"),
            sort=int(data.get("sort") or 0),
            status=int(data.get("status") if data.get("status") not in (None, "") else 1),
            remark=data.get("remark"),
            created_by=op,
            updated_by=op,
        )
        self.db.add(obj)
        await self.db.flush()
        return {"id": obj.id}

    async def data_update(self, data_id: int, data: dict[str, Any]) -> None:
        obj = await self.db.get(DictDataModel, data_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="字典数据不存在", code=1)
        for field in ("type_id", "label", "value", "color", "code", "sort", "remark"):
            if field in data:
                setattr(obj, field, data[field])
        if data.get("status") not in (None, ""):
            obj.status = int(data["status"])
        obj.updated_by = self._operator()
        await self.db.flush()

    async def data_delete(self, data_id: int) -> None:
        obj = await self.db.get(DictDataModel, data_id)
        if obj and not obj.delete_time:
            obj.delete_time = datetime.now()
            await self.db.flush()

    async def data_batch_delete(self, ids: list[int]) -> int:
        count = 0
        now = datetime.now()
        for did in ids:
            obj = await self.db.get(DictDataModel, did)
            if obj and not obj.delete_time:
                obj.delete_time = now
                count += 1
        await self.db.flush()
        return count

    async def data_status(self, data_id: int, status: int) -> None:
        obj = await self.db.get(DictDataModel, data_id)
        if not obj or obj.delete_time:
            raise CustomException(msg="字典数据不存在", code=1)
        obj.status = status
        obj.updated_by = self._operator()
        await self.db.flush()
