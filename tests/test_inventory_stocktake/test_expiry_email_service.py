from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXMaterialInfo
from app.inventory_stocktake.services.expiry_email_service import send_expiry_warning_emails
from app.models.enums import RoleType
from app.models.user import User


def test_send_expiry_warning_emails_collects_admin_and_store_manager(monkeypatch, db_session, store_r):
    # seed users
    admin = User(username="admin2", password_hash="x", role=RoleType.ADMIN, email="admin@test.com")
    manager = User(
        username="mgr",
        password_hash="x",
        role=RoleType.BRANCH_MANAGER,
        store_id=store_r.store_id,
        email="mgr@test.com",
    )
    db.session.add_all([admin, manager])

    # seed material + inventory check expiring in window
    db.session.add(
        MXMaterialInfo(
            material_code="E001",
            cn_name="临期物料",
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

    db.session.add(
        MXInventoryCheck(
            store_id=store_r.store_id,
            check_date=date(2026, 1, 31),
            material_code="E001",
            material_name="临期物料",
            spec_model="X",
            remaining_case_qty=1,
            remaining_group_qty=0,
            valid_until=date(2026, 2, 10),
            operator="admin",
        )
    )
    db.session.commit()

    captured = {}

    def fake_send(subject, recipients, body, html=None, async_send=True):
        captured["subject"] = subject
        captured["recipients"] = recipients
        captured["body"] = body
        return True

    monkeypatch.setattr("app.inventory_stocktake.services.expiry_email_service.send_notify_mail", fake_send)

    stats = send_expiry_warning_emails(today=date(2026, 2, 1), days_before=30, async_send=False)
    assert stats["stores"] == 1
    assert stats["emails_sent"] == 1
    assert "admin@test.com" in captured["recipients"]
    assert "mgr@test.com" in captured["recipients"]
    assert "临期物料" in captured["body"]
