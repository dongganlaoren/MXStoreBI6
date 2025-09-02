import datetime

from app.extensions import db
from app.models import Store, DailySales, User
from app.models.enums import FinancialCheckStatus, ReimbursementStatus, ReimbursementPrimaryCategory, \
    ReimbursementSecondaryCategory, RoleType
from app.models.reimbursement import ReimbursementRequest


def _login_admin(login, admin_user):
    return login(admin_user.username, "secret123")


def _yesterday():
    return datetime.date.today() - datetime.timedelta(days=1)


def _last_month_day():
    today = datetime.date.today()
    last_month = (today.replace(day=1) - datetime.timedelta(days=1))
    return last_month.replace(day=min(15, last_month.day))


def _mk_store(store_id="S1", name="Store1"):
    s = Store(store_id=store_id, store_name=name)
    db.session.add(s)
    db.session.commit()
    return s


def _mk_daily(store_id, d, pos_total=100.0, takeaway=10.0, actual=105.0, err=5.0):
    # 创建或获取一个用户来作为上报人
    user = User.query.filter_by(username=f"test_user_{store_id}").first()
    if not user:
        user = User(
            username=f"test_user_{store_id}",
            role=RoleType.EMPLOYEE,
            user_status=1,
            store_id=store_id
        )
        user.set_password("pw")
        db.session.add(user)
        db.session.commit()

    ds = DailySales(
        store_id=store_id,
        user_id=user.user_id,  # 添加必需的 user_id 字段
        report_date=d,
        pos_total=pos_total,
        takeaway_amount=takeaway,
        actual_sales=actual,
        total_error=err,
        financial_check_status=FinancialCheckStatus.APPROVED,
    )
    db.session.add(ds)
    db.session.commit()
    return ds


def _mk_reim(store_id, amt=50.0, day=None, submitter=None, approver=None):
    if day is None:
        day = _last_month_day()
    # 确保提交人与审批人存在
    if submitter is None:
        submitter = User(username=f"emp_reim_{store_id}", role=RoleType.EMPLOYEE, user_status=1, store_id=store_id)
        submitter.set_password("pw")
        db.session.add(submitter)
        db.session.commit()
    if approver is None:
        approver = User(username=f"fin_reim_{store_id}", role=RoleType.FINANCE, user_status=1)
        approver.set_password("pw")
        db.session.add(approver)
        db.session.commit()
    rr = ReimbursementRequest(
        store_id=store_id,
        submitter_id=submitter.user_id,
        approver_id=approver.user_id,
        primary_category=ReimbursementPrimaryCategory.SHARED_COST,
        secondary_category=list(ReimbursementSecondaryCategory)[0],
        amount=amt,
        currency='THB',
        description=f'测试报销 {store_id}',
        status=ReimbursementStatus.APPROVED,
        approved_at=datetime.datetime.combine(day, datetime.time(10, 0, 0)),
    )
    db.session.add(rr)
    db.session.commit()
    return rr


def test_report_center_pages_access_and_render(client, db_session, admin_user, login):
    # 登录管理员
    r_login = _login_admin(login, admin_user)
    assert r_login.status_code == 200

    # 准备基础数据
    s1 = _mk_store("S1", "门店1")
    s2 = _mk_store("S2", "门店2")
    # 日报：昨天两店各一条
    d = _yesterday()
    _mk_daily("S1", d)
    _mk_daily("S2", d)

    # 日/周/月页面应可访问
    r1 = client.get("/reports/daily")
    assert r1.status_code == 200
    assert "销售日报" in r1.get_data(as_text=True)

    r2 = client.get("/reports/weekly")
    assert r2.status_code == 200
    assert "销售周报" in r2.get_data(as_text=True)

    r3 = client.get("/reports/monthly")
    assert r3.status_code == 200
    assert "销售月报" in r3.get_data(as_text=True)

    # 成本统计页面（准备上月报销数据）
    _mk_reim("S1", 80.0)
    r4 = client.get("/reports/costs")
    assert r4.status_code == 200
    assert "成本统计" in r4.get_data(as_text=True)


def test_report_center_preview_and_send(client, db_session, admin_user, login, monkeypatch):
    _login_admin(login, admin_user)

    # 预览接口
    r_prev = client.get("/reports/preview?period=day")
    assert r_prev.status_code == 200
    assert "统计周期" in r_prev.get_data(as_text=True)

    # send_now 走邮件发送函数，打桩返回 True
    monkeypatch.setattr("app.utils.notify.send_sales_report_mail", lambda *args, **kwargs: True)
    r_send = client.post("/reports/send_now", data={"period": "day"}, follow_redirects=True)
    assert r_send.status_code == 200

    # send_by_filters 自定义收件人，走通知邮件发送（使用真实配置 suppress_send）
    r_send2 = client.post(
        "/reports/send_by_filters",
        data={
            "period": "day",
            "send_mode": "custom",
            "recipients": "a@ex.com,b@ex.com",
            "store_id": "",
            "start_date": "",
            "end_date": "",
        },
        follow_redirects=True,
    )
    assert r_send2.status_code == 200


def test_report_center_permission_denied_for_non_admin(client, db_session, login):
    # 准备一个普通员工
    u = User(username="emp1", role=RoleType.EMPLOYEE, user_status=1)
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()

    r_login = login("emp1", "pw")
    assert r_login.status_code == 200

    # 无权访问报表中心
    resp = client.get("/reports/daily", follow_redirects=True)
    assert resp.status_code == 200
    txt = resp.get_data(as_text=True)
    assert "无权限访问报表中心" in txt or "首页" in txt
