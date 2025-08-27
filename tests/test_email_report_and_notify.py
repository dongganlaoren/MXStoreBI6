from app.extensions import db
from app.models import User
from app.models.enums import RoleType


def test_email_report_config_get_and_save(client, db_session, monkeypatch):
    # 先创建一些角色用户，避免发送时过滤空
    u1 = User(username="u_admin", role=RoleType.ADMIN)
    u1.set_password("x")
    db.session.add(u1)
    db.session.commit()

    # GET 配置页
    r = client.get("/email_report/config")
    assert r.status_code == 200

    # POST 保存（不触发 send）
    payload = {"action": "save"}
    for role in ["ADMIN", "HEAD_MANAGER", "FINANCE", "BRANCH_MANAGER"]:
        payload[f"{role}_emails"] = ""
        payload[f"{role}_daily_enabled"] = "y"
        payload[f"{role}_weekly_enabled"] = ""
        payload[f"{role}_monthly_enabled"] = ""
        payload[f"{role}_daily_time"] = "20:00"
        payload[f"{role}_weekly_time"] = "10:00"
        payload[f"{role}_monthly_time"] = "10:00"
        payload[f"{role}_weekly_day"] = "1"
        payload[f"{role}_monthly_day"] = "1"

    r2 = client.post("/email_report/config", data=payload, follow_redirects=True)
    assert r2.status_code == 200


def test_email_report_manual_send(client, db_session, monkeypatch):
    # 构造用户，确保遍历到
    u1 = User(username="adm2", role=RoleType.ADMIN)
    u1.set_password("x")
    db.session.add(u1)
    db.session.commit()

    # mock 发送函数，始终 True
    monkeypatch.setattr("app.utils.notify.send_sales_report_mail", lambda *args, **kwargs: True)

    # 触发手动发送
    r = client.post("/email_report/config", data={"action": "send"}, follow_redirects=True)
    assert r.status_code == 200


def test_email_report_send_all_endpoint(client, db_session, monkeypatch):
    # 准备一个总部用户和一个分店长用户
    admin = User(username="u3", role=RoleType.ADMIN)
    admin.set_password("x")
    branch = User(username="u4", role=RoleType.BRANCH_MANAGER)
    branch.set_password("x")
    db.session.add_all([admin, branch])
    db.session.commit()

    # mock 邮件发送函数
    monkeypatch.setattr("app.utils.notify.send_sales_report_mail", lambda *args, **kwargs: True)

    r = client.get("/email_report/send_all?email=test@example.com")
    assert r.status_code == 200
    data = r.get_json()
    assert data["email"] == "test@example.com"


def test_send_notify_mail_empty_recipients(client, app):
    from app.utils.notify import send_notify_mail
    with app.app_context():
        ok = send_notify_mail("subj", [], "body")
        assert ok is True
