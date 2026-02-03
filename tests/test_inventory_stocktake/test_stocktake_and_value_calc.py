from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXMaterialInfo
from app.inventory_stocktake.services.stocktake_service import save_one
from app.inventory_stocktake.services.value_calc_service import UnitPriceMissingError, calc_values


def test_stocktake_save_and_calc_values(db_session, store_r):
    m = MXMaterialInfo(
        material_code="M010",
        cn_name="杯子",
        th_name=None,
        spec_model="S",
        per_group_qty=10,
        price_per_case=Decimal("20.00"),
        price_per_group=Decimal("2.00"),
        category="耗材",
        safety_stock=None,
        status="启用",
    )
    db.session.add(m)
    db.session.commit()

    d = date(2026, 1, 1)
    save_one(
        store_id=store_r.store_id,
        check_date=d,
        operator="admin",
        material_code="M010",
        material_name="杯子",
        spec_model="S",
        remaining_case_qty=2,
        remaining_group_qty=3,
    )

    details, cat_sum, total = calc_values(store_r.store_id, d)
    assert len(details) == 1
    assert details[0].value == Decimal("46.00")
    assert cat_sum["耗材"] == Decimal("46.00")
    assert total == Decimal("46.00")


def test_calc_values_missing_unit_price_raises(db_session, store_r):
    m = MXMaterialInfo(
        material_code="M011",
        cn_name="吸管",
        th_name=None,
        spec_model="S",
        per_group_qty=10,
        price_per_case=Decimal("1.00"),
        price_per_group=Decimal("1.00"),
        category="耗材",
        safety_stock=None,
        status="启用",
    )
    db.session.add(m)
    db.session.commit()

    # 通过 UPDATE 模拟“单价为空”的脏数据（满足需求中的异常处理场景）
    db.session.query(MXMaterialInfo).filter_by(material_code="M011").update({"price_per_group": None})
    db.session.commit()

    db.session.add(
        MXInventoryCheck(
            store_id=store_r.store_id,
            check_date=date(2026, 1, 2),
            material_code="M011",
            material_name="吸管",
            spec_model="S",
            remaining_case_qty=1,
            remaining_group_qty=1,
            operator="admin",
        )
    )
    db.session.commit()

    with pytest.raises(UnitPriceMissingError):
        calc_values(store_r.store_id, date(2026, 1, 2))
