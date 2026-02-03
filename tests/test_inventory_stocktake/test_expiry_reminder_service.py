from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXMaterialInfo
from app.inventory_stocktake.services.expiry_reminder_service import list_items_to_remind


def test_list_items_to_remind_filters_by_valid_until_window(db_session, store_r):
    # prepare materials
    db.session.add(
        MXMaterialInfo(
            material_code="M200",
            cn_name="测试物料",
            th_name=None,
            spec_model="X",
            per_group_qty=1,
            price_per_case=Decimal("1.00"),
            price_per_group=Decimal("1.00"),
            category="测试",
            safety_stock=None,
            status="启用",
        )
    )
    db.session.add(
        MXMaterialInfo(
            material_code="M201",
            cn_name="测试物料2",
            th_name=None,
            spec_model="X",
            per_group_qty=1,
            price_per_case=Decimal("1.00"),
            price_per_group=Decimal("1.00"),
            category="测试",
            safety_stock=None,
            status="启用",
        )
    )
    db.session.commit()

    # one item expiring in 10 days -> should be reminded
    db.session.add(
        MXInventoryCheck(
            store_id=store_r.store_id,
            check_date=date(2026, 1, 31),
            material_code="M200",
            material_name="测试物料",
            spec_model="X",
            remaining_case_qty=1,
            remaining_group_qty=0,
            valid_until=date(2026, 2, 10),
            operator="admin",
        )
    )

    # one item expiring in 60 days -> should not be reminded
    db.session.add(
        MXInventoryCheck(
            store_id=store_r.store_id,
            check_date=date(2026, 1, 31),
            material_code="M201",
            material_name="测试物料2",
            spec_model="X",
            remaining_case_qty=1,
            remaining_group_qty=0,
            valid_until=date(2026, 4, 1),
            operator="admin",
        )
    )
    db.session.commit()

    items = list_items_to_remind(today=date(2026, 2, 1), days_before=30)
    assert len(items) == 1
    assert items[0].material_code == "M200"
    assert items[0].valid_until == date(2026, 2, 10)
