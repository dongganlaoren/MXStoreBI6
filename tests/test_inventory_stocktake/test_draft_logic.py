from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo


def test_draft_store_scoped_persistence(client, admin_user, store_r):
    """Test Principle 1: Each store has 1 draft across all dates."""
    client.set_cookie("TEST_AUTH", "admin")

    # Setup materials
    m1 = MXMaterialInfo(
        material_code="TM001",
        cn_name="Material 1",
        spec_model="X",
        per_group_qty=1,
        price_per_case=Decimal("1.00"),
        price_per_group=Decimal("1.00"),
        category="Test",
        status="启用",
    )
    m2 = MXMaterialInfo(
        material_code="TM002",
        cn_name="Material 2",
        spec_model="X",
        per_group_qty=1,
        price_per_case=Decimal("1.00"),
        price_per_group=Decimal("1.00"),
        category="Test",
        status="启用",
    )
    db.session.add_all([m1, m2])
    db.session.commit()

    date1 = date(2026, 3, 1)
    date2 = date(2026, 3, 2)

    # 1. Save draft on Date 1 (M1=10, M2=20)
    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": date1.isoformat(),
            "items": [
                {"material_code": "TM001", "remaining_case_qty": 10, "remaining_group_qty": 0},
                {"material_code": "TM002", "remaining_case_qty": 20, "remaining_group_qty": 0}
            ],
        },
    )
    assert resp.status_code == 200, resp.text

    # 2. Verify load on Date 1
    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": date1.isoformat()},
    )
    items = resp.get_json()["data"]["items"]
    assert len(items) == 2
    items_map = {it["material_code"]: it for it in items}
    assert items_map["TM001"]["remaining_case_qty"] == 10

    # 3. Verify load on Date 2 (should return EMPTY because draft belongs to Date 1)
    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": date2.isoformat()},
    )
    items = resp.get_json()["data"]["items"]
    assert len(items) == 0, "Date 2 should not see Date 1 drafts"

    # 4. Save on Date 2 -> Should OVERWRITE store draft (clear old, set new)
    # Payload has only TM001. So TM002 (from Date 1) should be removed.
    resp = client.post(
        "/inventory-stocktake/api/stocktake/save-batch",
        json={
            "store_id": store_r.store_id,
            "check_date": date2.isoformat(),
            "items": [
                {"material_code": "TM001", "remaining_case_qty": 15, "remaining_group_qty": 0}
            ],
        },
    )
    assert resp.status_code == 200

    # 5. Verify load on Date 1 (Should be EMPTY, as it was overwritten by Date 2 save)
    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": date1.isoformat()},
    )
    items = resp.get_json()["data"]["items"]
    assert len(items) == 0, "Date 1 draft should be gone (overwritten)"

    # 6. Verify load on Date 2 (Should contain M1 only)
    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": date2.isoformat()},
    )
    items = resp.get_json()["data"]["items"]
    items_map = {it["material_code"]: it for it in items}

    # TM001: Updated by save
    assert "TM001" in items_map
    assert items_map["TM001"]["remaining_case_qty"] == 15

    # TM002: Should NOT exist
    assert "TM002" not in items_map, "TM002 should be removed by overwrite save"

    # 7. Commit on Date 2
    # This should commit ONLY M1.
    resp = client.post(
        "/inventory-stocktake/api/stocktake/commit",
        json={"store_id": store_r.store_id, "check_date": date2.isoformat()},
    )
    assert resp.status_code == 200

    # 8. Verify drafts cleared
    resp = client.get(
        "/inventory-stocktake/api/stocktake/draft",
        query_string={"store_id": store_r.store_id, "check_date": date2.isoformat()},
    )
    items = resp.get_json()["data"]["items"]
    assert len(items) == 0

    # 9. Verify committed data on Date 2
    resp = client.get(
        "/inventory-stocktake/api/stocktake/details",
        query_string={"store_id": store_r.store_id, "check_date": date2.isoformat()},
    )
    items = resp.get_json()["data"]["items"]
    items_map = {it["material_code"]: it for it in items}
    assert "TM001" in items_map
    assert "TM002" not in items_map
    assert items_map["TM001"]["remaining_case_qty"] == 15
