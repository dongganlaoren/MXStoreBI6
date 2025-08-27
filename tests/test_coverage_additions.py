import pytest
from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.forms.user_forms import RegistrationForm, EditProfileForm
from app.models import Store, User
from app.models.attachment import DailySalesAttachments
from app.models.enums import RoleType, ReimbursementStatus
from app.models.reimbursement import ReimbursementRequest
from app.utils import notify as notify_mod


@pytest.fixture()
def admin_logged_in(client, db_session):
    # 保证有 admin
    u = User(username="admin", role=RoleType.ADMIN, user_status=1)
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    client.post("/login", data={"username": "admin", "password": "secret123"}, follow_redirects=True)
    return u


def test_reimbursement_list_all_filters(client, db_session, admin_logged_in):
    # 准备数据：两个用户，两个申请
    submitter = User(username="u1", role=RoleType.EMPLOYEE, user_status=1)
    submitter.set_password("pw")
    approver = User(username="fa", role=RoleType.FINANCE, user_status=1)
    approver.set_password("pw")
    db.session.add_all([submitter, approver])
    db.session.commit()
    r1 = ReimbursementRequest(
        submitter_id=submitter.user_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=10,
        currency="THB",
        description="d1",
        status=ReimbursementStatus.PENDING,
        approver_id=approver.user_id,
    )
    r2 = ReimbursementRequest(
        submitter_id=submitter.user_id,
        primary_category="STORE_COST",
        secondary_category="MIXTURE_MATERIAL",
        amount=12,
        currency="THB",
        description="d2",
        status=ReimbursementStatus.APPROVED,
        approver_id=approver.user_id,
    )
    db.session.add_all([r1, r2])
    db.session.commit()
    # 访问 list_all 页
    r = client.get("/reimbursement/all")
    assert r.status_code == 200
    # 带过滤参数（无效日期格式亦应 200）
    r2 = client.get("/reimbursement/all?submitter=u1&approver=fa&start_date=bad&end_date=bad")
    assert r2.status_code == 200


def test_reimbursement_default_cc_config_post_paths(client, db_session, admin_logged_in):
    # 非法 user_id
    r = client.post("/reimbursement/default_cc_config", data={"action": "add", "user_id": "not-int"},
                    follow_redirects=True)
    assert r.status_code == 200
    # 禁用不存在的默认抄送人
    r2 = client.post("/reimbursement/default_cc_config", data={"action": "disable", "user_id": "999999"},
                     follow_redirects=True)
    assert r2.status_code == 200


def test_user_registration_form_validations(client, db_session):
    # 需要请求上下文用于 WTForms
    s = Store(store_id="T100", store_name="Test Store")
    db.session.add(s)
    db.session.commit()
    # 1) EMPLOYEE 未选门店 -> 失败
    formdata = MultiDict({
        "username": "alice",
        "password": "secret12",
        "confirm_password": "secret12",
        "role": "EMPLOYEE",
        # store_id 缺失
        "employee_number": ""
    })
    with client.application.test_request_context("/register", method="POST"):
        form = RegistrationForm(formdata=formdata, meta={'csrf': False})
        assert not form.validate()
    # 2) EMPLOYEE 已选门店但缺少员工编号 -> 失败
    formdata2 = MultiDict({
        "username": "bob1",
        "password": "secret12",
        "confirm_password": "secret12",
        "role": "EMPLOYEE",
        "store_id": s.store_id,
        "employee_number": ""
    })
    with client.application.test_request_context("/register", method="POST"):
        form2 = RegistrationForm(formdata=formdata2, meta={'csrf': False})
        assert not form2.validate()
    # 3) 员工编号格式错误 -> 失败
    formdata3 = MultiDict({
        "username": "charlie",
        "password": "secret12",
        "confirm_password": "secret12",
        "role": "EMPLOYEE",
        "store_id": s.store_id,
        "employee_number": "BAD"
    })
    with client.application.test_request_context("/register", method="POST"):
        form3 = RegistrationForm(formdata=formdata3, meta={'csrf': False})
        assert not form3.validate()
    # 4) 正确格式（门店号+三位数字） -> 通过
    emp_num = f"{s.store_id}001"
    formdata4 = MultiDict({
        "username": "dave",
        "password": "secret12",
        "confirm_password": "secret12",
        "role": "EMPLOYEE",
        "store_id": s.store_id,
        "employee_number": emp_num
    })
    with client.application.test_request_context("/register", method="POST"):
        form4 = RegistrationForm(formdata=formdata4, meta={'csrf': False})
        assert form4.validate()


def test_edit_profile_form_employee_number_validation(client, db_session):
    # 现有一个员工编号 123 的用户
    u = User(username="ex", role=RoleType.EMPLOYEE, user_status=1)
    u.set_password("pw")
    u.employee_number = 123
    db.session.add(u)
    db.session.commit()
    # 非数字 -> 失败
    formdata = MultiDict({
        "real_name": "Z",
        "role": "EMPLOYEE",
        "employee_number": "abc"
    })
    with client.application.test_request_context("/profile", method="POST"):
        form = EditProfileForm(formdata=formdata, meta={'csrf': False})
        assert not form.validate()
    # 重复编号 -> 失败
    formdata2 = MultiDict({
        "real_name": "Z",
        "role": "EMPLOYEE",
        "employee_number": "123"
    })
    with client.application.test_request_context("/profile", method="POST"):
        form2 = EditProfileForm(formdata=formdata2, meta={'csrf': False})
        assert not form2.validate()


def test_attachment_model_repr_and_to_dict(client, db_session, caplog):
    att = DailySalesAttachments(report_id=1, file_path="uploads/a.jpg")
    # 调用 __repr__（会写日志）
    txt = repr(att)
    assert "DailySalesAttachments" in txt
    d = att.to_dict()
    assert set(["attachment_id", "report_id", "file_path", "attachment_type", "created_at"]) - set(d.keys()) == set()


def test_notify_send_mail_sync_success(app, client, monkeypatch):
    # monkeypatch mail.send 为 no-op，避免真实发送
    class DummyMail:
        def send(self, msg):
            return None

    monkeypatch.setattr(notify_mod, "mail", DummyMail())
    with client.application.app_context():
        ok = notify_mod.send_notify_mail("S", ["a@b.com"], "body", async_send=False)
        assert ok is True


def test_send_sales_report_mail_branches(app, client, monkeypatch):
    # 无收件人 -> True
    with client.application.app_context():
        ok1 = notify_mod.send_sales_report_mail("day", RoleType.ADMIN, User(username="x"), [])
        assert ok1 is True

    # 数据不完整 -> False（mock query_sales_reports）
    def fake_query(period, role, user):
        return None, None, None, None, None

    monkeypatch.setattr(notify_mod, "query_sales_reports", fake_query)
    with client.application.app_context():
        ok2 = notify_mod.send_sales_report_mail("day", RoleType.ADMIN, User(username="x"), ["a@b.com"])
        assert ok2 is False
