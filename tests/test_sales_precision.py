from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pytest

from app.extensions import db
from app.models import DailySales, Store, User
from app.models.enums import RoleType, FinancialCheckStatus


def _d(x):
    return Decimal(str(x))


def _q4(x: Decimal) -> Decimal:
    return x.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


@pytest.fixture()
def store_with_takeaway(db_session):
    s = Store(store_id="P100", store_name="PrecisionStore", third_party_platform=True)
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def admin_for_precision(db_session, store_with_takeaway):
    u = User(username="prec_admin", role=RoleType.ADMIN, user_status=1)
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()
    return u


def test_precision_calculation_and_display(client, db_session, admin_for_precision, store_with_takeaway, login):
    # 准备含4位小数的金额
    cash = 100.1255
    pos = 200.3344
    day = 30.4444
    voucher = 10.5555
    t1 = 40.0005
    ea = 180.1299
    bc = 120.3399
    bf = 5.6789

    ds = DailySales(
        store_id=store_with_takeaway.store_id,
        user_id=admin_for_precision.user_id,
        report_date=date.today(),
        cash_income=cash,
        pos_income=pos,
        day_pass_income=day,
        voucher_amount=voucher,
        takeaway_amount=t1,
        electronic_actual_arrival=ea,
        bank_deposit=bc,
        bank_fee=bf,
        financial_check_status=FinancialCheckStatus.PENDING,
    )
    db.session.add(ds)
    ds.auto_calculate()
    db.session.commit()

    # 期望值（按4位小数四舍五入）
    exp_pos_total = _q4(_d(cash) + _d(pos) + _d(day) + _d(voucher))
    exp_theoretical_total = _q4(exp_pos_total + _d(t1) - _d(voucher) - _d(bf))
    exp_actual_sales = _q4(_d(t1) + _d(day) + _d(ea) + _d(bc))
    exp_total_error = _q4(_d(ea) + _d(bc) + _d(bf) - _d(pos) - _d(cash))

    # 模型字段按4位保存
    assert pytest.approx(float(exp_pos_total), rel=0, abs=1e-7) == ds.pos_total
    assert pytest.approx(float(exp_theoretical_total), rel=0, abs=1e-7) == ds.theoretical_total
    assert pytest.approx(float(exp_actual_sales), rel=0, abs=1e-7) == ds.actual_sales
    assert pytest.approx(float(exp_total_error), rel=0, abs=1e-7) == ds.total_error

    # 页面展示为2位小数
    login("prec_admin", "pw")
    r_list = client.get(f"/manage/list?store_id={store_with_takeaway.store_id}")
    assert r_list.status_code == 200
    exp_actual_2dp = f"{float(exp_actual_sales):.2f}".encode("utf-8")
    exp_pos_total_2dp = f"{float(exp_pos_total):.2f}".encode("utf-8")
    assert exp_actual_2dp in r_list.data
    assert exp_pos_total_2dp in r_list.data

    r_detail = client.get(f"/manage/detail/{ds.report_id}")
    assert r_detail.status_code == 200
    # 详情页显示的手续费/实收等也应为2位
    exp_bf_2dp = f"{bf:.2f}".encode("utf-8")
    assert exp_bf_2dp in r_detail.data
