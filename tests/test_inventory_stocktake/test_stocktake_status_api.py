from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo, MXStocktakeHeader


def test_stocktake_status_none(client, admin_user, store_r):
    client.set_cookie("TEST_AUTH", "admin")

    resp = client.get(
        "/inventory-stocktake/api/stocktake/status",
        query_string={"store_id": store_r.store_id, "check_date": date.today().isoformat()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["data"]["status"] == "NONE"


def test_stocktake_status_after_commit(client, admin_user, store_r):
    client.set_cookie("TEST_AUTH", "admin")

    # 准备物料
    db.session.add(
        MXMaterialInfo(
            material_code="M001",
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
    db.session.commit()

    check_date = date(2026, 1, 31)

    # 先保存一行草稿（创建 header）
    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": check_date.isoformat(),
            "items": [
                {
                    "material_code": "M001",
                    "remaining_case_qty": 1,
                    "remaining_group_qty": 2,
                    "valid_until": None,
                }
            ],
        },
    )
    assert resp.status_code == 200

    # 提交
    resp = client.post(
        "/inventory-stocktake/api/stocktake/commit",
        json={"store_id": store_r.store_id, "check_date": check_date.isoformat()},
    )
    assert resp.status_code == 200

    # 状态应为 COMMITTED
    resp = client.get(
        "/inventory-stocktake/api/stocktake/status",
        query_string={"store_id": store_r.store_id, "check_date": check_date.isoformat()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["data"]["status"] == "COMMITTED"


def test_stocktake_one_per_store_per_day_constraint(client, admin_user, store_r):
    client.set_cookie("TEST_AUTH", "admin")

    db.session.add(
        MXMaterialInfo(
            material_code="M002",
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

    check_date = date(2026, 2, 1)

    # first save creates header
    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": check_date.isoformat(),
            "items": [
                {"material_code": "M002", "remaining_case_qty": 0, "remaining_group_qty": 1, "valid_until": None}
            ],
        },
    )
    assert resp.status_code == 200

    # second save same store/date should not create another header
    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": check_date.isoformat(),
            "items": [
                {"material_code": "M002", "remaining_case_qty": 1, "remaining_group_qty": 0, "valid_until": None}
            ],
        },
    )
    assert resp.status_code == 200

    headers = MXStocktakeHeader.query.filter_by(store_id=store_r.store_id, check_date=check_date).all()
    assert len(headers) == 1


def test_stocktake_details_load_after_commit(client, admin_user, store_r):
    client.set_cookie("TEST_AUTH", "admin")

    db.session.add(
        MXMaterialInfo(
            material_code="M003",
            cn_name="测试物料3",
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

    check_date = date(2026, 2, 2)

    # save draft
    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": check_date.isoformat(),
            "items": [
                {"material_code": "M003", "remaining_case_qty": 2, "remaining_group_qty": 3, "valid_until": None}
            ],
        },
    )
    assert resp.status_code == 200

    # commit
    resp = client.post(
        "/inventory-stocktake/api/stocktake/commit",
        json={"store_id": store_r.store_id, "check_date": check_date.isoformat()},
    )
    assert resp.status_code == 200

    # after commit, draft should be automatically cleared
    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": check_date.isoformat()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["data"]["items"] == []

    # committed details should remain loadable (read-only)
    resp = client.get(
        "/inventory-stocktake/api/stocktake/details",
        query_string={"store_id": store_r.store_id, "check_date": check_date.isoformat()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    items = data["data"]["items"]
    assert any(
        it["material_code"] == "M003" and it["remaining_case_qty"] == 2 and it["remaining_group_qty"] == 3 for it in
        items)


def test_stocktake_draft_api_loads_saved_draft(client, admin_user, store_r):
    client.set_cookie("TEST_AUTH", "admin")

    db.session.add(
        MXMaterialInfo(
            material_code="M004",
            cn_name="测试物料4",
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

    check_date = date(2026, 2, 3)

    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": check_date.isoformat(),
            "items": [
                {"material_code": "M004", "remaining_case_qty": 5, "remaining_group_qty": 6, "valid_until": None}
            ],
        },
    )
    assert resp.status_code == 200

    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": check_date.isoformat()},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    items = data["data"]["items"]
    assert any(
        it["material_code"] == "M004" and it["remaining_case_qty"] == 5 and it["remaining_group_qty"] == 6 for it in
        items)
