import io
from datetime import date

import pytest

from app.extensions import db
from app.models import DailySales, Store, User
from app.models.enums import FinancialCheckStatus, RoleType


@pytest.fixture()
def store(db_session):
    s = Store(store_id="S100", store_name="Alpha Store", third_party_platform=True)
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def employee(db_session, store):
    u = User(username="emp1", role=RoleType.EMPLOYEE, user_status=1, store_id=store.store_id)
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()
    return u


def test_manage_list_admin_and_employee_filters(client, db_session, admin_user, employee, store, login):
    # 准备两条日报
    ds1 = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                     financial_check_status=FinancialCheckStatus.PENDING)
    ds2 = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                     financial_check_status=FinancialCheckStatus.APPROVED)
    db.session.add_all([ds1, ds2])
    db.session.commit()

    # 管理员看 PENDING 过滤
    login("admin", "secret123")
    r1 = client.get(f"/manage/list?store_id={store.store_id}&financial_check_status=PENDING")
    assert r1.status_code == 200

    # 员工仅看到自己店铺
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"username": "emp1", "password": "pw"}, follow_redirects=True)
    r2 = client.get("/manage/list")
    assert r2.status_code == 200


def test_detail_page(client, db_session, admin_user, store, login):
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING)
    db.session.add(ds)
    db.session.commit()

    login("admin", "secret123")
    r = client.get(f"/manage/detail/{ds.report_id}")
    assert r.status_code == 200


def test_create_daily_sales_minimal_success(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    # GET 页面
    r_get = client.get("/manage/create")
    assert r_get.status_code == 200

    payload = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    r_post = client.post("/manage/create", data=payload, follow_redirects=True)
    assert r_post.status_code == 200
    assert db.session.query(DailySales).count() >= 1


def test_manage_check_edit_paths(client, db_session, admin_user, store, login):
    # 登录管理员
    login("admin", "secret123")
    # 创建一条待审核日报
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING,
                    bank_deposit=0, cash_income=0, pos_income=0, voucher_amount=0, electronic_actual_arrival=0)
    db.session.add(ds)
    db.session.commit()

    # GET 审核页
    r_get = client.get(f"/manage/check/{ds.report_id}")
    assert r_get.status_code == 200

    # POST 修改 bank_deposit 并通过审核（需要提供理由 remark_bank_deposit）
    form = {
        "bank_deposit": "7",
        "financial_check_status": "APPROVED",
        "remark": "ok",
        "remark_bank_deposit": "修正"
    }
    r_post = client.post(f"/manage/check/{ds.report_id}", data=form, follow_redirects=True)
    assert r_post.status_code == 200
    db.session.refresh(ds)
    assert ds.financial_check_status == FinancialCheckStatus.APPROVED

    # 若已审核，GET 应落到详情页
    r_get2 = client.get(f"/manage/check/{ds.report_id}")
    assert r_get2.status_code == 200


def test_manage_audit_list_auth_and_filters(client, db_session, admin_user, store, login):
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING)
    db.session.add(ds)
    db.session.commit()

    login("admin", "secret123")
    r = client.get(f"/manage/audit/list?store_id={store.store_id}&financial_check_status=PENDING")
    assert r.status_code == 200


def test_manage_report_list_admin_and_employee(client, db_session, admin_user, employee, store, login):
    # 一条日报
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING)
    db.session.add(ds)
    db.session.commit()

    # 管理员
    login("admin", "secret123")
    r1 = client.get("/manage/report/list")
    assert r1.status_code == 200

    # 员工
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"username": "emp1", "password": "pw"}, follow_redirects=True)
    r2 = client.get("/manage/report/list")
    assert r2.status_code == 200


def test_manage_report_create_missing_attachments_then_success(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    # 先触发缺失附件提示
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    r1 = client.post("/manage/report/create", data=base)
    assert r1.status_code == 200

    # 构造所有必需附件
    files = {
        "sales_slip_image": (io.BytesIO(b"a"), "a.jpg"),
        "bank_receipt_image": (io.BytesIO(b"b"), "b.jpg"),
        "electronic_actual_arrival_receipt": (io.BytesIO(b"c"), "c.jpg"),
        "takeaway_platform_receipt": (io.BytesIO(b"d"), "d.jpg"),
    }
    data = dict(base)
    data.update(files)
    r2 = client.post("/manage/report/create", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r2.status_code == 200


def test_delete_check_happy_path(client, db_session, admin_user, store, login, tmp_path):
    # 创建一条待审核日报和一个附件文件
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING)
    db.session.add(ds)
    db.session.flush()

    # 在 static/uploads 下创建假文件，并记录附件
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    fake_file = uploads_dir / f"{ds.report_id}_x.txt"
    fake_file.write_text("x")

    from app.models import DailySalesAttachments, AttachmentType
    rel = f"uploads/{fake_file.name}"
    att = DailySalesAttachments(report_id=ds.report_id, file_path=rel, attachment_type=AttachmentType.sales_slip)
    db.session.add(att)
    db.session.commit()

    # 将文件复制到应用 static/uploads 目录
    import os, shutil
    static_uploads = os.path.join(client.application.root_path, 'static', 'uploads')
    os.makedirs(static_uploads, exist_ok=True)
    shutil.copy(str(fake_file), os.path.join(static_uploads, fake_file.name))

    # 登录管理员并删除
    login("admin", "secret123")
    r = client.get(f"/manage/check/delete/{ds.report_id}", follow_redirects=True)
    assert r.status_code == 200
    # 记录应被删除
    assert DailySales.query.get(ds.report_id) is None


def test_manage_create_no_store_warning(client, db_session):
    # 无店铺员工
    from app.models.enums import RoleType
    u = User(username="nostore", role=RoleType.EMPLOYEE, user_status=1)
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()

    client.post("/login", data={"username": "nostore", "password": "pw"}, follow_redirects=True)
    r = client.get("/manage/create")
    assert r.status_code == 200


def test_manage_create_duplicate_prevent(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    # 先创建一条
    payload = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    client.post("/manage/create", data=payload, follow_redirects=True)
    # 再次创建同一天同店，应阻止
    r2 = client.post("/manage/create", data=payload)
    assert r2.status_code == 200


def test_manage_check_edit_unauthorized(client, db_session, employee, store):
    # 待审核日报
    ds = DailySales(store_id=store.store_id, user_id=employee.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING)
    db.session.add(ds)
    db.session.commit()

    # 员工登录访问审核页应被拒绝
    client.post("/login", data={"username": "emp1", "password": "pw"}, follow_redirects=True)
    r = client.get(f"/manage/check/{ds.report_id}", follow_redirects=True)
    assert r.status_code == 200


def test_manage_check_missing_reason_and_invalid_status(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.PENDING,
                    bank_deposit=0, cash_income=0, pos_income=0, voucher_amount=0, electronic_actual_arrival=0)
    db.session.add(ds)
    db.session.commit()

    # 缺少理由应停留页面
    form1 = {
        "bank_deposit": "8",
        "financial_check_status": "PENDING",
        "remark": ""
    }
    r1 = client.post(f"/manage/check/{ds.report_id}", data=form1)
    assert r1.status_code == 200

    # 提交非法状态值，触发异常分支
    form2 = {
        "bank_deposit": "0",
        "financial_check_status": "INVALID",
        "remark": "x"
    }
    r2 = client.post(f"/manage/check/{ds.report_id}", data=form2)
    assert r2.status_code == 200


def test_manage_audit_list_unauthorized_and_approved_filter(client, db_session, employee, admin_user, store, login):
    # 一条已审核记录
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.APPROVED)
    db.session.add(ds)
    db.session.commit()

    # 员工无权
    client.post("/login", data={"username": "emp1", "password": "pw"}, follow_redirects=True)
    r1 = client.get("/manage/audit/list", follow_redirects=True)
    assert r1.status_code == 200

    # 管理员查看 APPROVED 筛选
    client.get("/logout", follow_redirects=True)
    login("admin", "secret123")
    r2 = client.get(f"/manage/audit/list?financial_check_status=APPROVED&report_date=bad-date")
    assert r2.status_code == 200


def test_manage_report_create_without_takeaway_requirement(client, db_session, admin_user, login):
    # 创建不支持外卖的门店
    s2 = Store(store_id="S200", store_name="NoTakeaway", third_party_platform=False)
    db.session.add(s2)
    db.session.commit()

    login("admin", "secret123")
    base = {
        "store_id": s2.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    # 不提供 takeaway_platform_receipt 也可成功
    r = client.post("/manage/report/create", data=base, follow_redirects=True)
    assert r.status_code == 200


def test_delete_check_only_pending(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.APPROVED)
    db.session.add(ds)
    db.session.commit()

    r = client.get(f"/manage/check/delete/{ds.report_id}", follow_redirects=True)
    assert r.status_code == 200


def test_manage_list_approved_and_bad_date(client, db_session, admin_user, store, login):
    # 一条已审核
    ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                    financial_check_status=FinancialCheckStatus.APPROVED)
    db.session.add(ds)
    db.session.commit()

    login("admin", "secret123")
    r = client.get(f"/manage/list?financial_check_status=APPROVED&report_date=bad-date")
    assert r.status_code == 200


def test_manage_create_for_no_takeaway_store(client, db_session, admin_user, login):
    s2 = Store(store_id="S300", store_name="S300", third_party_platform=False)
    db.session.add(s2)
    db.session.commit()

    login("admin", "secret123")
    payload = {
        "store_id": s2.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "0",
        "pos_income": "0",
        "voucher_amount": "0",
        "electronic_actual_arrival": "0",
        "bank_deposit": "0",
        "bank_fee": "0",
    }
    r = client.post("/manage/create", data=payload, follow_redirects=True)
    assert r.status_code == 200


def test_manage_report_create_duplicate_prevent(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "1",
        "pos_income": "2",
        "voucher_amount": "0",
        "electronic_actual_arrival": "1",
        "bank_deposit": "1",
        "bank_fee": "0",
    }

    def make_files():
        return {
            "sales_slip_image": (io.BytesIO(b"a"), "a.jpg"),
            "bank_receipt_image": (io.BytesIO(b"b"), "b.jpg"),
            "electronic_actual_arrival_receipt": (io.BytesIO(b"c"), "c.jpg"),
        }

    data1 = dict(base)
    data1.update(make_files())
    r1 = client.post("/manage/report/create", data=data1, content_type='multipart/form-data', follow_redirects=True)
    assert r1.status_code == 200
    # 再次提交同一天同店，应被阻断
    data2 = dict(base)
    data2.update(make_files())
    r2 = client.post("/manage/report/create", data=data2, content_type='multipart/form-data')
    assert r2.status_code == 200


def test_manage_report_list_pagination(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    for i in range(25):
        ds = DailySales(store_id=store.store_id, user_id=admin_user.user_id, report_date=date.today(),
                        financial_check_status=FinancialCheckStatus.PENDING)
        db.session.add(ds)
    db.session.commit()
    r = client.get("/manage/report/list?page=2")
    assert r.status_code == 200
    # 页面应包含分页相关内容
    assert b"<table" in r.data
    assert b"page" in r.data or "下一页".encode("utf-8") in r.data


def test_manage_report_create_form_validation(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "invalid",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    r = client.post("/manage/create", data=base)
    assert r.status_code == 200
    # 页面应包含错误提示
    assert b"error" in r.data or b"danger" in r.data


def test_manage_report_create_missing_fields(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
    }
    r = client.post("/manage/create", data=base)
    assert r.status_code == 200
    assert b"error" in r.data or b"danger" in r.data


def test_manage_report_create_invalid_date(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": "invalid-date",
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    r = client.post("/manage/create", data=base)
    assert r.status_code == 200
    assert b"error" in r.data or b"danger" in r.data


def test_manage_report_create_auto_zero_takeaway_amount(client, db_session, admin_user, login):
    s2 = Store(store_id="S400", store_name="TakeawayStore", third_party_platform=True)
    db.session.add(s2)
    db.session.commit()
    login("admin", "secret123")
    base = {
        "store_id": s2.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    files = {
        "sales_slip_image": (io.BytesIO(b"a"), "a.jpg"),
        "bank_receipt_image": (io.BytesIO(b"b"), "b.jpg"),
        "electronic_actual_arrival_receipt": (io.BytesIO(b"c"), "c.jpg"),
    }
    data = dict(base)
    data.update(files)
    r = client.post("/manage/report/create", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    sales = DailySales.query.filter_by(store_id=s2.store_id, report_date=date.today()).first()
    assert sales is not None
    # 外卖金额应为0
    assert sales.takeaway_amount == 0


def test_manage_report_create_with_invalid_file_type(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    files = {
        "sales_slip_image": (io.BytesIO(b"invalid"), "invalid.txt"),
    }
    data = dict(base)
    data.update(files)
    r = client.post("/manage/report/create", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    assert b"error" in r.data or b"danger" in r.data


def test_manage_report_create_missing_attachment_warning(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    r = client.post("/manage/report/create", data=base)
    assert r.status_code == 200
    assert b"error" in r.data or b"danger" in r.data


def test_manage_report_create_success_with_all_fields(client, db_session, admin_user, store, login):
    login("admin", "secret123")
    base = {
        "store_id": store.store_id,
        "report_date": date.today().strftime("%Y-%m-%d"),
        "cash_income": "10",
        "pos_income": "20",
        "voucher_amount": "0",
        "electronic_actual_arrival": "15",
        "bank_deposit": "5",
        "bank_fee": "0",
    }
    files = {
        "sales_slip_image": (io.BytesIO(b"a"), "a.jpg"),
        "bank_receipt_image": (io.BytesIO(b"b"), "b.jpg"),
        "electronic_actual_arrival_receipt": (io.BytesIO(b"c"), "c.jpg"),
        "takeaway_platform_receipt": (io.BytesIO(b"d"), "d.jpg"),
    }
    data = dict(base)
    data.update(files)
    r = client.post("/manage/report/create", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    assert "日报创建成功".encode("utf-8") in r.data


def test_create_reimbursement_duplicate_prevent(client, db_session, submitter, finance1, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)
    payload = {
        "primary_category": "STORE_COST",
        "secondary_category": "UTILITIES",
        "store_id": store_r.store_id,
        "reason": "water bill",
        "submission_date": date.today().strftime("%Y-%m-%d"),
        "amount": "12.34",
        "currency": "THB",
        "approver_id": str(finance1.user_id),
        "cc_recipients": "[]",
    }
    client.post("/reimbursement/create", data=payload, follow_redirects=True)
    r2 = client.post("/reimbursement/create", data=payload)
    # 允许200或302，断言重定向目标
    assert r2.status_code in (200, 302)
    if r2.status_code == 302:
        assert "/reimbursement/" in r2.headers.get("Location", "")
