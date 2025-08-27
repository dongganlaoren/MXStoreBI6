from datetime import date

from app.extensions import db
from app.models import DailySales, Store, User
from app.models.enums import RoleType, FinancialCheckStatus


def test_daily_sales_auto_calculate(db_session):
    s = Store(store_id="93001", store_name="门店93001")
    db.session.add(s)
    u = User(username="sales", role=RoleType.EMPLOYEE, store_id="93001")
    u.set_password("x")
    db.session.add(u)
    db.session.commit()

    ds = DailySales(
        store_id="93001",
        user_id=u.user_id,
        report_date=date(2024, 1, 2),
        cash_income=100,
        pos_income=200,
        day_pass_income=30,
        voucher_amount=10,
        electronic_actual_arrival=180,
        bank_deposit=120,
        bank_fee=5,
        takeaway_amount=40,
        financial_check_status=FinancialCheckStatus.APPROVED,
    )
    db.session.add(ds)
    ds.auto_calculate()
    db.session.commit()

    # T0 = 100 + 200 + 30 + 10 = 340
    assert round(ds.pos_total, 2) == 340.00
    # T2 = T0 + T1 - voucher - bank_fee = 340 + 40 - 10 - 5 = 365
    assert round(ds.theoretical_total, 2) == 365.00
    # S = T1 + 外卖收入 + EA + BC = 40 + 30 + 180 + 120 = 370
    assert round(ds.actual_sales, 2) == 370.00
    # E = EA + BC + BF - POS电子 - 现金 = 180 + 120 + 5 - 200 - 100 = 5
    assert round(ds.total_error, 2) == 5.00

    data = ds.to_dict()
    assert data["financial_check_status"] == "APPROVED"
