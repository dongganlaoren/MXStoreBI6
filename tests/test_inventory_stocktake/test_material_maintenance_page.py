from __future__ import annotations

from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo


def test_material_template_download_route(client, admin_user, login):
    login("admin", "secret123")
    resp = client.get("/inventory-stocktake/material/template")
    assert resp.status_code == 200
    # attachment filename
    cd = resp.headers.get("Content-Disposition", "")
    assert "inventory_stocktake_template.xlsx" in cd


def test_material_update_one_post(client, admin_user, login, db_session):
    login("admin", "secret123")

    db.session.add(
        MXMaterialInfo(
            material_code="T100",
            cn_name="测试物料",
            th_name=None,
            spec_model="X",
            per_group_qty=1,
            price_per_case=Decimal("1.00"),
            price_per_group=Decimal("2.00"),
            category="测试",
            safety_stock=None,
            status="启用",
        )
    )
    db.session.commit()

    resp = client.post(
        "/inventory-stocktake/material",
        data={
            "action": "update_one",
            "material_code": "T100",
            "cn_name": "测试物料2",
            "spec_model": "Y",
            "category": "测试2",
            "status": "禁用",
            "price_per_case": "",
            "price_per_group": "3.5",
            "safety_stock": "10",
            "remark": "r",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    m = MXMaterialInfo.query.filter_by(material_code="T100").first()
    assert m is not None
    assert m.cn_name == "测试物料2"
    assert m.spec_model == "Y"
    assert m.category == "测试2"
    assert m.status == "禁用"
    assert m.price_per_case is None
    assert float(m.price_per_group) == 3.5
    assert m.safety_stock == 10
    assert m.remark == "r"
