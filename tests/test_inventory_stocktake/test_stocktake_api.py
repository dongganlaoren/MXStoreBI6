from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXMaterialInfo


def test_stocktake_api_save_with_valid_until(client, app, admin_user, store_r):
    # ensure admin login via cookie is enabled in tests
    client.set_cookie("TEST_AUTH", "admin")

    db.session.add(
        MXMaterialInfo(
            material_code="A001",
            cn_name="可过期物料",
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

    resp = client.post(
        "/inventory-stocktake/api/stocktake/save",
        json={
            "store_id": store_r.store_id,
            "check_date": "2026-01-31",
            "material_code": "A001",
            "material_name": "可过期物料",
            "spec_model": "X",
            "remaining_case_qty": 1,
            "remaining_group_qty": 2,
            "valid_until": "2026-02-15",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True

    rec = MXInventoryCheck.query.filter_by(store_id=store_r.store_id, material_code="A001").first()
    assert rec is not None
    assert rec.valid_until == date(2026, 2, 15)
