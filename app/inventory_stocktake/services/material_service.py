from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo
from app.inventory_stocktake.utils.excel_parser import ParsedMaterialRow
from app.inventory_stocktake.utils.validators import ValidationError


@dataclass
class ImportItemResult:
    row_number: int
    success: bool
    message: str


@dataclass
class ImportSummary:
    success_count: int
    fail_count: int
    results: List[ImportItemResult]


def upsert_materials(rows: List[ParsedMaterialRow]) -> ImportSummary:
    """按需求处理 Excel 导入：支持新增/更新混合，单行原子，允许部分成功。"""

    results: List[ImportItemResult] = []
    ok = 0
    fail = 0

    for r in rows:
        try:
            _upsert_one(r)
            ok += 1
            results.append(ImportItemResult(r.row_number, True, "成功"))
        except ValidationError as e:
            db.session.rollback()
            fail += 1
            results.append(ImportItemResult(r.row_number, False, str(e)))
        except Exception as e:
            db.session.rollback()
            fail += 1
            results.append(ImportItemResult(r.row_number, False, f"导入失败：{e}"))

    return ImportSummary(success_count=ok, fail_count=fail, results=results)


def _upsert_one(row: ParsedMaterialRow) -> None:
    d = row.data
    op_type = d["operation_type"]
    code = d["material_code"]

    existing: Optional[MXMaterialInfo] = MXMaterialInfo.query.filter_by(material_code=code).first()

    if op_type == "新增":
        if existing is not None:
            raise ValidationError(f"第{row.row_number}行：物料编码已存在，新增模式不允许重复")
        m = MXMaterialInfo(
            material_code=code,
            cn_name=d["cn_name"],
            th_name=d.get("th_name"),
            spec_model=d["spec_model"],
            per_group_qty=d["per_group_qty"],
            price_per_case=d["price_per_case"],
            price_per_group=d["price_per_group"],
            category=d["category"],
            safety_stock=d.get("safety_stock"),
            status=d["status"],
            product_image=d.get("product_image"),
            remark=d.get("remark"),
        )
        db.session.add(m)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValidationError(f"第{row.row_number}行：物料编码重复") from e
        return

    if op_type == "更新":
        if existing is None:
            raise ValidationError(f"第{row.row_number}行：更新模式下物料编码不存在")

        # 仅更新非空字段：这里对 None 视为“空”
        for attr, key in [
            ("cn_name", "cn_name"),
            ("th_name", "th_name"),
            ("spec_model", "spec_model"),
            ("per_group_qty", "per_group_qty"),
            ("price_per_case", "price_per_case"),
            ("price_per_group", "price_per_group"),
            ("category", "category"),
            ("safety_stock", "safety_stock"),
            ("status", "status"),
            ("product_image", "product_image"),
            ("remark", "remark"),
        ]:
            v = d.get(key)
            if v is None:
                continue
            setattr(existing, attr, v)

        db.session.commit()
        return

    raise ValidationError(f"第{row.row_number}行：未知操作类型")
