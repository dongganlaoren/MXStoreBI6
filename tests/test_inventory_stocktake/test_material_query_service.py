from __future__ import annotations

from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo
from app.inventory_stocktake.services.material_query_service import search_materials


def test_search_materials_by_code_and_pagination(db_session):
    # seed
    for i in range(1, 6):
        db.session.add(
            MXMaterialInfo(
                material_code=f"Q{i}",
                cn_name=f"物料{i}",
                th_name=None,
                spec_model="S",
                per_group_qty=1,
                price_per_case=Decimal("1.00"),
                price_per_group=Decimal("1.00"),
                category="测试",
                safety_stock=None,
                status="启用",
            )
        )
    db.session.commit()

    rows, total = search_materials(q="Q", page=1, page_size=2)
    assert total >= 5
    assert len(rows) == 2

    rows2, _ = search_materials(q="Q", page=2, page_size=2)
    assert len(rows2) == 2
