import pytest

from app.extensions import db
from app.models import User, Store
from app.models.enums import RoleType, ReimbursementStatus
from app.models.reimbursement import ReimbursementRequest


@pytest.fixture()
def store_x(db_session):
    s = Store(store_id="RX1", store_name="RStore1")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def users_for_reimb(db_session, store_x):
    submitter = User(username="subx", role=RoleType.EMPLOYEE, user_status=1, store_id=store_x.store_id,
                     email="s@ex.com")
    submitter.set_password("pw")
    other = User(username="othx", role=RoleType.EMPLOYEE, user_status=1, store_id=store_x.store_id)
    other.set_password("pw")
    fin1 = User(username="finx1", role=RoleType.FINANCE, user_status=1, email="f1@ex.com")
    fin1.set_password("pw")
    fin2 = User(username="finx2", role=RoleType.FINANCE, user_status=1, email="f2@ex.com")
    fin2.set_password("pw")
    db.session.add_all([submitter, other, fin1, fin2])
    db.session.commit()
    return submitter, other, fin1, fin2


def _make_req(submitter_id, approver_id, store_id, status=ReimbursementStatus.PENDING):
    r = ReimbursementRequest(
        submitter_id=submitter_id,
        store_id=store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=10,
        currency="THB",
        description="x",
        status=status,
        approver_id=approver_id,
    )
    db.session.add(r)
    db.session.commit()
    return r


def test_withdraw_non_pending_and_permissions(client, db_session, users_for_reimb, login, store_x):
    sub, other, fin1, fin2 = users_for_reimb
    # 非待审批，撤回失败
    r = _make_req(sub.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.APPROVED)
    login("subx", "pw")
    resp = client.post(f"/reimbursement/{r.request_id}/withdraw", follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(r)
    assert r.status == ReimbursementStatus.APPROVED
    # 非本人撤回失败
    r2 = _make_req(sub.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.PENDING)
    client.get("/logout", follow_redirects=True)
    login("othx", "pw")
    resp2 = client.post(f"/reimbursement/{r2.request_id}/withdraw", follow_redirects=True)
    assert resp2.status_code == 200
    db.session.refresh(r2)
    assert r2.status == ReimbursementStatus.PENDING


def test_edit_permissions_and_status(client, db_session, users_for_reimb, login, store_x):
    sub, other, fin1, fin2 = users_for_reimb
    # 非草稿编辑失败（待审批）
    r = _make_req(sub.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.PENDING)
    login("subx", "pw")
    resp = client.post(f"/reimbursement/{r.request_id}/edit", data={"reason": "new"}, follow_redirects=True)
    assert resp.status_code == 200
    # 他人草稿也不可编辑
    r2 = _make_req(other.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.DRAFT)
    resp2 = client.post(f"/reimbursement/{r2.request_id}/edit", data={"reason": "new"}, follow_redirects=True)
    assert resp2.status_code == 200


def test_delete_permissions(client, db_session, users_for_reimb, login, store_x):
    sub, other, fin1, fin2 = users_for_reimb
    # 非草稿删除失败
    r = _make_req(sub.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.PENDING)
    login("subx", "pw")
    resp = client.post(f"/reimbursement/{r.request_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    # 他人草稿删除失败
    r2 = _make_req(other.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.DRAFT)
    resp2 = client.post(f"/reimbursement/{r2.request_id}/delete", follow_redirects=True)
    assert resp2.status_code == 200


def test_transfer_approver_permission_and_input(client, db_session, users_for_reimb, login, store_x):
    sub, other, fin1, fin2 = users_for_reimb
    r = _make_req(sub.user_id, fin1.user_id, store_x.store_id, status=ReimbursementStatus.PENDING)
    # 非当前审批人尝试转交 -> 失败
    login("finx2", "pw")
    resp = client.post(f"/reimbursement/{r.request_id}/transfer", data={"new_approver_id": fin2.user_id},
                       follow_redirects=True)
    assert resp.status_code == 200
    # 当前审批人但未提供新审批人 -> 失败
    client.get("/logout", follow_redirects=True)
    login("finx1", "pw")
    resp2 = client.post(f"/reimbursement/{r.request_id}/transfer", data={}, follow_redirects=True)
    assert resp2.status_code == 200
    # 新审批人无权限（用普通员工） -> 失败
    resp3 = client.post(f"/reimbursement/{r.request_id}/transfer", data={"new_approver_id": sub.user_id},
                        follow_redirects=True)
    assert resp3.status_code == 200


def test_approver_and_cc_search_endpoints(client, db_session, users_for_reimb, login):
    sub, other, fin1, fin2 = users_for_reimb
    login("finx1", "pw")
    r1 = client.get("/reimbursement/approver_search?q=finx")
    assert r1.status_code == 200
    r2 = client.get("/reimbursement/cc_recipients_search?q=subx")
    assert r2.status_code == 200
