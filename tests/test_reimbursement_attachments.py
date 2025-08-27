import io
from datetime import date

from app.extensions import db
from app.models import User, Store
from app.models.enums import RoleType, ReimbursementStatus
from app.models.reimbursement import ReimbursementRequest, ReimbursementAttachment


def test_reimbursement_create_with_attachments(client, db_session, monkeypatch):
    # 禁用真实发信
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 基础数据
    s = Store(store_id="AX1", store_name="AStore")
    sub = User(username="asub", role=RoleType.EMPLOYEE, user_status=1, store_id=s.store_id)
    sub.set_password("pw")
    fin = User(username="afin", role=RoleType.FINANCE, user_status=1, email="afin@ex.com")
    fin.set_password("pw")
    db.session.add_all([s, sub, fin])
    db.session.commit()
    # 登录并提交包含附件的创建
    client.post("/login", data={"username": "asub", "password": "pw"}, follow_redirects=True)
    data = {
        "primary_category": "STORE_COST",
        "secondary_category": "UTILITIES",
        "store_id": s.store_id,
        "reason": "fee",
        "submission_date": date.today().strftime("%Y-%m-%d"),
        "amount": "9.99",
        "currency": "THB",
        "approver_id": str(fin.user_id),
        "cc_recipients": "[]",
        "attachments": (io.BytesIO(b"img"), "test.jpg")
    }
    r = client.post("/reimbursement/create", data=data, content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    req = ReimbursementRequest.query.order_by(ReimbursementRequest.request_id.desc()).first()
    assert req is not None
    atts = ReimbursementAttachment.query.filter_by(request_id=req.request_id).all()
    assert len(atts) >= 1


def test_reimbursement_approve_with_attachment(client, db_session, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 基础数据：创建一条待审批
    s = Store(store_id="AX2", store_name="AStore2")
    sub = User(username="bsub", role=RoleType.EMPLOYEE, user_status=1, store_id=s.store_id)
    sub.set_password("pw")
    fin = User(username="bfin", role=RoleType.FINANCE, user_status=1, email="bfin@ex.com")
    fin.set_password("pw")
    db.session.add_all([s, sub, fin])
    db.session.commit()
    req = ReimbursementRequest(
        submitter_id=sub.user_id,
        store_id=s.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=10,
        currency="THB",
        description="fee",
        status=ReimbursementStatus.PENDING,
        approver_id=fin.user_id,
    )
    db.session.add(req)
    db.session.commit()
    # 审批人登录并上传审批附件
    client.post("/login", data={"username": "bfin", "password": "pw"}, follow_redirects=True)
    data = {
        "approval_comments": "ok",
        # 'status' 可空，视图中直接设置通过
    }
    files = {
        "attachments": (io.BytesIO(b"img"), "approve.jpg")
    }
    r = client.post(f"/reimbursement/{req.request_id}/approve", data={**data, **files},
                    content_type='multipart/form-data', follow_redirects=True)
    assert r.status_code == 200
    db.session.refresh(req)
    assert req.status == ReimbursementStatus.APPROVED
    atts = ReimbursementAttachment.query.filter_by(request_id=req.request_id).all()
    assert len(atts) >= 1
