from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from flask import current_app

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXMaterialInfo


class UnitPriceMissingError(RuntimeError):
    pass


@dataclass
class MaterialValueRow:
    material_code: str
    material_name: str
    category: str
    remaining_case_qty: int
    remaining_group_qty: int
    price_per_case: Decimal
    price_per_group: Decimal
    value: Decimal


def calc_values(store_id: str, check_date) -> Tuple[List[MaterialValueRow], Dict[str, Decimal], Decimal]:
    """计算单物料/类别/总货值。

    返回：
      - 明细列表
      - 类别汇总 dict
      - 总货值

    异常策略：单价为空则抛异常（需求要求）并记录日志。
    """

    q = (
        db.session.query(MXInventoryCheck, MXMaterialInfo)
        .join(MXMaterialInfo, MXMaterialInfo.material_code == MXInventoryCheck.material_code)
        .filter(MXInventoryCheck.store_id == store_id, MXInventoryCheck.check_date == check_date)
    )

    details: List[MaterialValueRow] = []
    category_sum: Dict[str, Decimal] = {}
    total = Decimal("0.00")

    for inv, mat in q.all():
        if mat.price_per_case is None or mat.price_per_group is None:
            msg = f"物料{mat.material_code}单价为空，无法计算货值"
            try:
                current_app.logger.error(msg)
            except Exception:
                pass
            raise UnitPriceMissingError(msg)

        value = (Decimal(inv.remaining_case_qty) * Decimal(mat.price_per_case)) + (
                Decimal(inv.remaining_group_qty) * Decimal(mat.price_per_group)
        )
        value = value.quantize(Decimal("1.00"))

        row = MaterialValueRow(
            material_code=inv.material_code,
            material_name=inv.material_name,
            category=mat.category,
            remaining_case_qty=inv.remaining_case_qty,
            remaining_group_qty=inv.remaining_group_qty,
            price_per_case=Decimal(mat.price_per_case),
            price_per_group=Decimal(mat.price_per_group),
            value=value,
        )
        details.append(row)
        category_sum[row.category] = category_sum.get(row.category, Decimal("0.00")) + value
        total += value

    for k in list(category_sum.keys()):
        category_sum[k] = category_sum[k].quantize(Decimal("1.00"))

    return details, category_sum, total.quantize(Decimal("1.00"))
