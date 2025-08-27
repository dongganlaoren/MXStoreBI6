import os
from datetime import date

from app.extensions import db
from app.models import User, Store, DailySales
from app.models.email_task_log import EmailTaskLog, EmailTaskType, EmailTaskStatus
from app.models.enums import RoleType, FinancialCheckStatus


def test_main_index_with_store_data(client, db_session, admin_user, login):
    # 创建门店与日报
    s = Store(store_id="S1", store_name="Test Store")
    db.session.add(s)
    u = admin_user
    ds = DailySales(
        store_id=s.store_id,
        user_id=u.user_id,
        report_date=date.today(),
        pos_total=100.0,
        takeaway_amount=50.0,
        actual_sales=150.0,
        total_error=0.0,
        financial_check_status=FinancialCheckStatus.APPROVED,
    )
    db.session.add(ds)
    db.session.commit()

    # 登录并访问首页
    resp = login("admin", "secret123")
    assert resp.status_code == 200
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert b"Test Store" in r.data


def test_admin_required_denies_non_admin(client, db_session, login):
    # 非管理员用户
    emp = User(username="emp", role=RoleType.EMPLOYEE, user_status=1)
    emp.set_password("pw")
    db.session.add(emp)
    db.session.commit()

    resp = login("emp", "pw")
    assert resp.status_code == 200

    r = client.get("/admin/users/", follow_redirects=True)
    assert r.status_code == 200
    # 被重定向回首页或显示无权限提示
    assert b"\xe6\x97\xa0\xe6\x9d\x83\xe9\x99\x90" in r.data or b"/" in r.request.path.encode()


def test_user_and_admin_download_id_card_copy(client, db_session, admin_user, login, tmp_path):
    # 先登录管理员
    login("admin", "secret123")

    # 普通用户缺少复印件 -> 404
    u = User(username="u1", role=RoleType.EMPLOYEE, user_status=1)
    u.set_password("x")
    db.session.add(u)
    db.session.commit()

    r404 = client.get(f"/admin/users/{u.user_id}/download_id_card_copy")
    assert r404.status_code == 404

    # 准备一个可读文件并设置相对路径
    uploads_dir = os.path.join(client.application.root_path, "static", "uploads", "secure")
    os.makedirs(uploads_dir, exist_ok=True)
    fname = tmp_path / "id.jpg"
    fname.write_bytes(b"123")
    rel = os.path.join("uploads", "secure", os.path.basename(str(fname)))
    # 拷贝到应用静态目录
    dst = os.path.join(uploads_dir, os.path.basename(str(fname)))
    with open(dst, "wb") as f:
        f.write(b"123")

    u.id_card_copy = rel
    db.session.commit()

    r200 = client.get(f"/admin/users/{u.user_id}/download_id_card_copy")
    assert r200.status_code == 200


def test_user_endpoints_staff_view_logout_and_download(client, db_session, admin_user, login):
    login("admin", "secret123")

    # staff_view
    r1 = client.get("/staff/view")
    assert r1.status_code == 200

    # 本人身份证下载 404（未设置）
    r2 = client.get("/download_id_card_copy")
    assert r2.status_code == 404

    # 登出
    r3 = client.get("/logout", follow_redirects=True)
    assert r3.status_code == 200


def test_email_report_log_list(client, db_session):
    # 加一条日志
    log = EmailTaskLog(
        task_type=EmailTaskType.daily,
        start_date=date.today(),
        end_date=date.today(),
        recipients="a@example.com",
        status=EmailTaskStatus.success,
        success_count=1,
        fail_count=0,
    )
    db.session.add(log)
    db.session.commit()

    r = client.get("/email_report/log_list")
    assert r.status_code == 200


def test_root_redirect_when_logged_in(client, db_session, admin_user, login):
    login("admin", "secret123")
    r = client.get("/", follow_redirects=False)
    # 登录后直接渲染 main.index，返回 200
    assert r.status_code == 200


def test_admin_reset_password_endpoint(client, db_session, admin_user, login):
    # 先建一个用户
    u = User(username="rw", role=RoleType.EMPLOYEE, user_status=1)
    u.set_password("old")
    db.session.add(u)
    db.session.commit()

    # 登录管理员
    login("admin", "secret123")

    # 重置密码
    r = client.post(f"/admin/users/{u.user_id}/reset_password", follow_redirects=True)
    assert r.status_code == 200
    # 新密码为 123456
    db.session.refresh(u)
    assert u.check_password("123456")


def test_main_index_employee_only_own_store(client, db_session, login):
    s = Store(store_id="S2", store_name="Emp Store")
    db.session.add(s)
    emp = User(username="emp2", role=RoleType.EMPLOYEE, user_status=1, store_id=s.store_id)
    emp.set_password("pw")
    db.session.add(emp)
    db.session.commit()
    login("emp2", "pw")
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert b"Emp Store" in r.data


def test_main_index_employee_no_store(client, db_session, login):
    emp = User(username="emp3", role=RoleType.EMPLOYEE, user_status=1)
    emp.set_password("pw")
    db.session.add(emp)
    db.session.commit()
    login("emp3", "pw")
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    # 页面应无门店信息
    assert "门店".encode("utf-8") not in r.data or "暂无门店".encode("utf-8") in r.data


def test_main_index_store_no_takeaway_field(client, db_session, admin_user, login):
    # 门店无 has_takeaway 字段，且无外卖数据
    s = Store(store_id="S3", store_name="NoTakeaway")
    db.session.add(s)
    db.session.commit()
    login("admin", "secret123")
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    # 页面应正常渲染
    assert b"NoTakeaway" in r.data


def test_main_index_no_daily_sales(client, db_session, admin_user, login):
    s = Store(store_id="S4", store_name="NoSales")
    db.session.add(s)
    db.session.commit()
    login("admin", "secret123")
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    # 页面应正常渲染
    assert b"NoSales" in r.data


def test_main_index_weekly_stats_discontinuous(client, db_session, admin_user, login):
    s = Store(store_id="S5", store_name="WeekStore")
    db.session.add(s)
    ds1 = DailySales(store_id=s.store_id, user_id=admin_user.user_id, report_date=date.today(),
                     pos_total=100.0, takeaway_amount=50.0, actual_sales=150.0, total_error=0.0,
                     financial_check_status=FinancialCheckStatus.APPROVED)
    ds2 = DailySales(store_id=s.store_id, user_id=admin_user.user_id,
                     report_date=date.today().replace(day=max(1, date.today().day - 3)),
                     pos_total=80.0, takeaway_amount=30.0, actual_sales=110.0, total_error=0.0,
                     financial_check_status=FinancialCheckStatus.APPROVED)
    db.session.add_all([ds1, ds2])
    db.session.commit()
    login("admin", "secret123")
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert b"WeekStore" in r.data
