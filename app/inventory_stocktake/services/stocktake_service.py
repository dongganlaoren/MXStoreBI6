from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXMaterialInfo
from app.inventory_stocktake.utils.validators import ValidationError, parse_non_negative_int, require_non_empty


@dataclass
class SaveResult:
    success: bool
    message: str


def save_one(
        *,
        store_id: str,
        check_date: date,
        operator: Optional[str],
        material_code: str,
        material_name: str,
        spec_model: Optional[str],
        remaining_case_qty,
        remaining_group_qty,
        valid_until: Optional[date] = None,
) -> SaveResult:
    """保存单条盘点记录（存在则覆盖数量），校验物料编码必须存在。"""

    store_id = require_non_empty(store_id, "店铺")
    material_code = require_non_empty(material_code, "物料编码")
    material_name = require_non_empty(material_name, "物料名称")

    case_qty = parse_non_negative_int(remaining_case_qty, "剩余整件数")
    group_qty = parse_non_negative_int(remaining_group_qty, "剩余散件数")

    if MXMaterialInfo.query.filter_by(material_code=material_code).first() is None:
        raise ValidationError("物料编码不存在于物料信息表")

    existing = MXInventoryCheck.query.filter_by(
        store_id=store_id, check_date=check_date, material_code=material_code
    ).first()

    if existing is None:
        rec = MXInventoryCheck(
            store_id=store_id,
            check_date=check_date,
            material_code=material_code,
            material_name=material_name,
            spec_model=spec_model,
            remaining_case_qty=case_qty,
            remaining_group_qty=group_qty,
            valid_until=valid_until,
            operator=operator,
            operated_at=datetime.utcnow(),
        )
        db.session.add(rec)
    else:
        existing.material_name = material_name
        existing.spec_model = spec_model
        existing.remaining_case_qty = case_qty
        existing.remaining_group_qty = group_qty
        existing.valid_until = valid_until
        existing.operator = operator
        existing.operated_at = datetime.utcnow()

    db.session.commit()
    return SaveResult(True, "保存成功")


def save_batch(
        *,
        store_id: str,
        check_date: date,
        operator: Optional[str],
        items: List[dict],
) -> SaveResult:
    """批量保存：逐条校验逐条写入，出现异常时回滚当条并继续（允许部分成功）。"""

    ok = 0
    fail = 0
    for it in items:
        try:
            save_one(
                store_id=store_id,
                check_date=check_date,
                operator=operator,
                material_code=it.get("material_code"),
                material_name=it.get("material_name"),
                spec_model=it.get("spec_model"),
                remaining_case_qty=it.get("remaining_case_qty"),
                remaining_group_qty=it.get("remaining_group_qty"),
                valid_until=it.get("valid_until"),
            )
            ok += 1
        except Exception:
            db.session.rollback()
            fail += 1

    return SaveResult(True, f"批量保存完成：成功{ok}条，失败{fail}条")


def reset(store_id: str, check_date: date) -> int:
    """清空指定店铺指定日期的盘点数据。"""
    q = MXInventoryCheck.query.filter_by(store_id=store_id, check_date=check_date)
    n = q.count()
    q.delete(synchronize_session=False)
    db.session.commit()
    return n
