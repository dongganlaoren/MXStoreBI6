from __future__ import annotations

from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo
from app.inventory_stocktake.services.material_service import upsert_materials
from app.inventory_stocktake.utils.excel_parser import ParsedMaterialRow


def test_material_import_add_and_update(db_session):
    rows = [
        ParsedMaterialRow(
            row_number=2,
            data={
                "operation_type": "新增",
                "material_code": "M001",
                "cn_name": "糖",
                "th_name": None,
                "spec_model": "1kg",
                "per_group_qty": 10,
                "price_per_case": Decimal("100.00"),
                "price_per_group": Decimal("10.00"),
                "category": "原料",
                "safety_stock": 1,
                "status": "启用",
                "product_image": "path/to/img",
                "remark": None,
            },
        ),
        ParsedMaterialRow(
            row_number=3,
            data={
                "operation_type": "更新",
                "material_code": "M001",
                "cn_name": "白砂糖",
                "th_name": None,
                "spec_model": "1kg",
                "per_group_qty": 10,
                "price_per_case": Decimal("100.00"),
                "price_per_group": Decimal("10.00"),
                "category": "原料",
                "safety_stock": None,
                "status": "启用",
                "product_image": None,
                "remark": "updated",
            },
        ),
    ]

    summary = upsert_materials(rows)
    assert summary.success_count == 2
    assert summary.fail_count == 0

    m = MXMaterialInfo.query.filter_by(material_code="M001").first()
    assert m is not None
    assert m.cn_name == "白砂糖"
    assert m.remark == "updated"
    # 更新模式 product_image 为 None 不应覆盖原值
    assert m.product_image == "path/to/img"


def test_material_import_add_duplicate_should_fail(db_session):
    m = MXMaterialInfo(
        material_code="M002",
        cn_name="奶",
        th_name=None,
        spec_model="1L",
        per_group_qty=1,
        price_per_case=Decimal("1.00"),
        price_per_group=Decimal("1.00"),
        category="原料",
        safety_stock=None,
        status="启用",
    )
    db.session.add(m)
    db.session.commit()

    rows = [
        ParsedMaterialRow(
            row_number=2,
            data={
                "operation_type": "新增",
                "material_code": "M002",
                "cn_name": "奶",
                "th_name": None,
                "spec_model": "1L",
                "per_group_qty": 1,
                "price_per_case": Decimal("1.00"),
                "price_per_group": Decimal("1.00"),
                "category": "原料",
                "safety_stock": None,
                "status": "启用",
                "product_image": None,
                "remark": None,
            },
        )
    ]

    summary = upsert_materials(rows)
    assert summary.success_count == 0
    assert summary.fail_count == 1
    assert "已存在" in summary.results[0].message
