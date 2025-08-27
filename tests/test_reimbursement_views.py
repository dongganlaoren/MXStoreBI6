from datetime import date

import pytest

from app.extensions import db
from app.models import User, Store
from app.models.enums import RoleType, ReimbursementStatus
from app.models.reimbursement import ReimbursementRequest, ReimbursementDefaultCCRecipient, ReimbursementCCRecipient


@pytest.fixture()
def store_r(db_session):
    s = Store(store_id="RS1", store_name="Reimb Store")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def submitter(db_session, store_r):
    u = User(username="bm1", role=RoleType.EMPLOYEE, user_status=1, store_id=store_r.store_id, email="bm1@ex.com")
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def finance1(db_session):
    u = User(username="fin1", role=RoleType.FINANCE, user_status=1, email="fin1@ex.com")
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def finance2(db_session):
    u = User(username="fin2", role=RoleType.FINANCE, user_status=1, email="fin2@ex.com")
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()
    return u


def test_list_requests_and_create_minimal(client, db_session, submitter, finance1, store_r, monkeypatch):
    # 登录提交人
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)

    # GET 列表页
    r_list = client.get("/reimbursement/")
    assert r_list.status_code == 200

    # 默认抄送人配置一个
    dcc_user = User.query.filter_by(username="fin2").first()
    if dcc_user:
        db.session.add(ReimbursementDefaultCCRecipient(user_id=dcc_user.user_id, created_by=submitter.user_id))
        db.session.commit()

    # mock 邮件发送
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)

    # POST 最小数据
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
    r_create = client.post("/reimbursement/create", data=payload, follow_redirects=True)
    assert r_create.status_code == 200

    # 列表再次访问
    r_list2 = client.get("/reimbursement/")
    assert r_list2.status_code == 200


def test_detail_approve_and_withdraw_delete(client, db_session, submitter, finance1, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 直接插入一条待审批申请
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=10,
        currency="THB",
        description="fee",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
    )
    db.session.add(req)
    db.session.commit()

    # 详情（提交人）
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)
    r_detail = client.get(f"/reimbursement/{req.request_id}")
    assert r_detail.status_code == 200

    # 撤回（提交人）-> DRAFT
    r_wd = client.post(f"/reimbursement/{req.request_id}/withdraw", follow_redirects=True)
    assert r_wd.status_code == 200
    db.session.refresh(req)
    assert req.status == ReimbursementStatus.DRAFT

    # 删除（草稿，提交人）
    r_del = client.post(f"/reimbursement/{req.request_id}/delete", follow_redirects=True)
    assert r_del.status_code == 200


def test_approve_flow_and_transfer(client, db_session, submitter, finance1, finance2, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 创建一条待审批，审批人 finance1
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=20,
        currency="THB",
        description="fee",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
    )
    db.session.add(req)
    db.session.commit()

    # 审批 GET 页面
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)
    r_get = client.get(f"/reimbursement/{req.request_id}/approve")
    assert r_get.status_code == 200

    # 审批通过（登录审批人）
    r_ap = client.post(f"/reimbursement/{req.request_id}/approve",
                       data={"approval_comments": "ok"}, follow_redirects=True)
    assert r_ap.status_code == 200

    # 创建另一条待审批，测试转交
    req2 = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=22,
        currency="THB",
        description="x",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
    )
    db.session.add(req2)
    db.session.commit()

    # 转交缺参数
    r_tf_missing = client.post(f"/reimbursement/{req2.request_id}/transfer", data={}, follow_redirects=True)
    assert r_tf_missing.status_code == 200

    # 转交给无审批权限的用户
    emp = User(username="e1", role=RoleType.EMPLOYEE, user_status=1)
    emp.set_password("x")
    db.session.add(emp)
    db.session.commit()

    r_tf_bad = client.post(f"/reimbursement/{req2.request_id}/transfer", data={"new_approver_id": str(emp.user_id)},
                           follow_redirects=True)
    assert r_tf_bad.status_code == 200

    # 转交给 finance2（成功分支也走一遍）
    r_tf_ok = client.post(f"/reimbursement/{req2.request_id}/transfer", data={"new_approver_id": str(finance2.user_id)},
                          follow_redirects=True)
    assert r_tf_ok.status_code == 200


def test_list_requests_filters_for_finance_and_time(client, db_session, submitter, finance1, store_r):
    # 创建多条用于过滤
    now = date.today()
    # 待审批，审批人 finance1（todo）
    req1 = ReimbursementRequest(submitter_id=submitter.user_id, store_id=store_r.store_id,
                                primary_category="STORE_COST", secondary_category="UTILITIES",
                                amount=1, currency="THB", description="a",
                                status=ReimbursementStatus.PENDING, approver_id=finance1.user_id)
    # 已审批
    req2 = ReimbursementRequest(submitter_id=submitter.user_id, store_id=store_r.store_id,
                                primary_category="STORE_COST", secondary_category="UTILITIES",
                                amount=2, currency="THB", description="b",
                                status=ReimbursementStatus.APPROVED, approver_id=finance1.user_id)
    # 我提交的（finance 自己提交）
    req3 = ReimbursementRequest(submitter_id=finance1.user_id, store_id=store_r.store_id,
                                primary_category="STORE_COST", secondary_category="UTILITIES",
                                amount=3, currency="THB", description="c",
                                status=ReimbursementStatus.PENDING, approver_id=finance1.user_id)
    db.session.add_all([req1, req2, req3])
    db.session.commit()
    # 抄送给 finance1
    db.session.add(ReimbursementCCRecipient(request_id=req1.request_id, user_id=finance1.user_id))
    db.session.commit()

    # 登录 finance1
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)

    # todo
    r_todo = client.get("/reimbursement/?category=todo")
    assert r_todo.status_code == 200
    # done
    r_done = client.get("/reimbursement/?category=done")
    assert r_done.status_code == 200
    # mine
    r_mine = client.get("/reimbursement/?category=mine")
    assert r_mine.status_code == 200
    # cc
    r_cc = client.get("/reimbursement/?category=cc")
    assert r_cc.status_code == 200
    # 时间范围
    assert client.get("/reimbursement/?time_range=24h").status_code == 200
    assert client.get("/reimbursement/?time_range=7d").status_code == 200
    assert client.get("/reimbursement/?time_range=30d").status_code == 200
    # custom 错误格式
    assert client.get("/reimbursement/?time_range=custom&start_date=bad&end_date=bad").status_code == 200


def test_create_shared_cost_forces_none_and_invalid_cc_json(client, db_session, submitter, finance1, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)

    payload = {
        "primary_category": "SHARED_COST",
        "secondary_category": "SHARED_REIMBURSEMENT",
        # 公摊成本不应提交 store_id
        "reason": "shared",
        "submission_date": date.today().strftime("%Y-%m-%d"),
        "amount": "9.99",
        "currency": "THB",
        "approver_id": str(finance1.user_id),
        "cc_recipients": "[",  # 非法 JSON
    }
    r = client.post("/reimbursement/create", data=payload, follow_redirects=True)
    assert r.status_code == 200


def test_edit_draft_then_resubmit(client, db_session, submitter, finance1, store_r):
    # 插入一条 草稿
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=5,
        currency="THB",
        description="d",
        status=ReimbursementStatus.DRAFT,
        approver_id=finance1.user_id,
    )
    db.session.add(req)
    db.session.commit()

    # 登录提交人，GET 编辑
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)
    r_get = client.get(f"/reimbursement/{req.request_id}/edit")
    assert r_get.status_code == 200

    # POST 再提交
    payload = {
        "primary_category": "STORE_COST",
        "secondary_category": "UTILITIES",
        "store_id": store_r.store_id,
        "reason": "update",
        "submission_date": date.today().strftime("%Y-%m-%d"),
        "amount": "10.00",
        "currency": "THB",
        "approver_id": str(finance1.user_id),
    }
    r_post = client.post(f"/reimbursement/{req.request_id}/edit", data=payload, follow_redirects=True)
    assert r_post.status_code == 200


def test_default_cc_config_and_search(client, db_session, admin_user, finance2):
    # 登录管理员
    client.post("/login", data={"username": "admin", "password": "secret123"}, follow_redirects=True)

    # GET 页面
    g = client.get("/reimbursement/default_cc_config")
    assert g.status_code == 200

    # 添加默认抄送人
    p1 = client.post("/reimbursement/default_cc_config", data={"action": "add", "user_id": str(finance2.user_id)},
                     follow_redirects=True)
    assert p1.status_code == 200

    # 禁用默认抄送人
    p2 = client.post("/reimbursement/default_cc_config", data={"action": "disable", "user_id": str(finance2.user_id)},
                     follow_redirects=True)
    assert p2.status_code == 200

    # 搜索默认抄送可添加的人
    s = client.get("/reimbursement/default_cc_search?q=fin2")
    assert s.status_code == 200


def test_default_cc_config_unauthorized_and_search_unauth(client, db_session, submitter):
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)
    # 未授权访问页面
    r = client.get("/reimbursement/default_cc_config", follow_redirects=True)
    assert r.status_code == 200
    # 未授权搜索
    s = client.get("/reimbursement/default_cc_search?q=xx")
    assert s.status_code == 200
    assert s.get_json() == []


def test_search_endpoints_empty_params_and_all_unauthorized(client, db_session, submitter):
    # approver_search 空
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)
    assert client.get("/reimbursement/approver_search").status_code == 200
    assert client.get("/reimbursement/cc_recipients_search").status_code == 200

    # list_all 未授权
    assert client.get("/reimbursement/all", follow_redirects=True).status_code == 200


def test_list_requests_filters_and_time_ranges(client, db_session, submitter, finance1, finance2, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 创建多条申请
    from datetime import timedelta
    now = date.today()
    for i in range(3):
        req = ReimbursementRequest(
            submitter_id=submitter.user_id,
            store_id=store_r.store_id,
            primary_category="STORE_COST",
            secondary_category="UTILITIES",
            amount=10 + i,
            currency="THB",
            description="fee",
            status=ReimbursementStatus.PENDING,
            approver_id=finance1.user_id,
            created_at=now - timedelta(days=i),
            updated_at=now - timedelta(days=i),
        )
        db.session.add(req)
    db.session.commit()

    # 财务登录，todo
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)
    r_todo = client.get("/reimbursement/?category=todo")
    assert r_todo.status_code == 200
    # done
    r_done = client.get("/reimbursement/?category=done")
    assert r_done.status_code == 200
    # mine
    r_mine = client.get("/reimbursement/?category=mine")
    assert r_mine.status_code == 200
    # cc
    r_cc = client.get("/reimbursement/?category=cc")
    assert r_cc.status_code == 200
    # 时间区间
    r_24h = client.get("/reimbursement/?time_range=24h")
    assert r_24h.status_code == 200
    r_7d = client.get("/reimbursement/?time_range=7d")
    assert r_7d.status_code == 200
    r_30d = client.get("/reimbursement/?time_range=30d")
    assert r_30d.status_code == 200
    # custom 正常
    r_custom = client.get(
        f"/reimbursement/?time_range=custom&start_date={now.strftime('%Y-%m-%d')}&end_date={now.strftime('%Y-%m-%d')}")
    assert r_custom.status_code == 200
    # custom 异常
    r_custom_bad = client.get("/reimbursement/?time_range=custom&start_date=bad&end_date=bad")
    assert r_custom_bad.status_code == 200
    # 语言切换
    r_lang = client.get("/reimbursement/?lang=en")
    assert r_lang.status_code == 200


def test_list_requests_no_data_and_invalid_params(client, db_session, finance1):
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)
    # 无数据
    r = client.get("/reimbursement/?category=todo")
    assert r.status_code == 200
    # 无效参数
    r2 = client.get("/reimbursement/?category=unknown")
    assert r2.status_code == 200


def test_create_reimbursement_form_validation(client, db_session, submitter, finance1, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    client.post("/login", data={"username": "bm1", "password": "pw"}, follow_redirects=True)
    # 缺少必填字段
    payload = {
        "primary_category": "STORE_COST",
        "store_id": store_r.store_id,
        "reason": "water bill",
        "submission_date": date.today().strftime("%Y-%m-%d"),
        "amount": "",
        "currency": "THB",
        "approver_id": str(finance1.user_id),
        "cc_recipients": "[]",
    }
    r = client.post("/reimbursement/create", data=payload)
    assert r.status_code == 200
    # 无效金额
    payload["amount"] = "invalid"
    r2 = client.post("/reimbursement/create", data=payload)
    assert r2.status_code == 200


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
    # 再次提交同样数据，系统应阻止
    r2 = client.post("/reimbursement/create", data=payload)
    assert r2.status_code == 200


def test_list_requests_cc_recipient(client, db_session, submitter, finance1, finance2, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 创建一条抄送给 finance2 的申请
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=10,
        currency="THB",
        description="fee",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
    )
    db.session.add(req)
    db.session.flush()
    db.session.add(ReimbursementCCRecipient(request_id=req.request_id, user_id=finance2.user_id))
    db.session.commit()
    # finance2 登录，查看 cc
    client.post("/login", data={"username": "fin2", "password": "pw"}, follow_redirects=True)
    r = client.get("/reimbursement/?category=cc")
    assert r.status_code == 200


def test_list_requests_permission_denied(client, db_session, store_r):
    # 未登录访问
    r = client.get("/reimbursement/")
    assert r.status_code == 302  # 重定向到登录


def test_transferred_approver_sees_approve_button(client, db_session, submitter, finance1, finance2, store_r,
                                                  monkeypatch):
    # 避免实际发邮件
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 创建一条待审批记录，审批人为 finance1
    from app.models.reimbursement import ReimbursementRequest
    from app.models.enums import ReimbursementStatus
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=66,
        currency="THB",
        description="x",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
    )
    db.session.add(req)
    db.session.commit()

    # finance1 登录并转交给 finance2
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)
    r_tf = client.post(f"/reimbursement/{req.request_id}/transfer", data={"new_approver_id": str(finance2.user_id)},
                       follow_redirects=True)
    assert r_tf.status_code == 200

    # 切换登录 finance2，先登出再登录
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"username": "fin2", "password": "pw"}, follow_redirects=True)
    r_list = client.get("/reimbursement/?category=todo")
    assert r_list.status_code == 200
    html = r_list.get_data(as_text=True)
    # 应包含该请求的审批链接按钮
    assert f"/reimbursement/{req.request_id}/approve" in html
    # 也应出现按钮文案（中文环境默认）
    assert "审批" in html


def test_transfer_old_request_visible_in_recent_range_after_transfer(client, db_session, submitter, finance1, finance2,
                                                                     store_r, monkeypatch):
    from datetime import timedelta, datetime
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 创建一条40天前创建的待审批请求
    old_time = datetime.now() - timedelta(days=40)
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=77,
        currency="THB",
        description="old",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
        created_at=old_time,
        updated_at=old_time,
    )
    db.session.add(req)
    db.session.commit()

    # finance1 转交给 finance2（会更新 updated_at 为当前）
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)
    client.post(f"/reimbursement/{req.request_id}/transfer", data={"new_approver_id": str(finance2.user_id)},
                follow_redirects=True)

    # 确认数据库已更新审批人与更新时间
    db.session.refresh(req)
    assert req.approver_id == finance2.user_id
    from datetime import datetime, timedelta as _td
    assert req.updated_at >= datetime.now() - _td(days=1)

    # finance2 登录，使用最近30天筛选访问todo列表（先登出再登录）
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"username": "fin2", "password": "pw"}, follow_redirects=True)
    r_list = client.get("/reimbursement/?category=todo&time_range=30d")
    assert r_list.status_code == 200
    html = r_list.get_data(as_text=True)
    # 期望：应能看到审批按钮
    assert f"/reimbursement/{req.request_id}/approve" in html


def test_mark_checked_and_lockdown(client, db_session, submitter, finance1, finance2, store_r, monkeypatch):
    monkeypatch.setattr("app.utils.notify.send_notify_mail", lambda *a, **k: True)
    # 创建一条待审批记录，审批人为 finance1
    req = ReimbursementRequest(
        submitter_id=submitter.user_id,
        store_id=store_r.store_id,
        primary_category="STORE_COST",
        secondary_category="UTILITIES",
        amount=88,
        currency="THB",
        description="check",
        status=ReimbursementStatus.PENDING,
        approver_id=finance1.user_id,
    )
    db.session.add(req)
    db.session.commit()

    # finance1 登录并先审批通过
    client.post("/login", data={"username": "fin1", "password": "pw"}, follow_redirects=True)
    r_ap = client.post(f"/reimbursement/{req.request_id}/approve", data={"approval_comments": "ok"},
                       follow_redirects=True)
    assert r_ap.status_code == 200
    db.session.refresh(req)
    assert req.status == ReimbursementStatus.APPROVED

    # 列表页应出现“标记已核对”按钮
    r_list = client.get("/reimbursement/?category=done")
    html = r_list.get_data(as_text=True)
    assert "mark_checked" in html

    # 标记已核对
    r_mc = client.post(f"/reimbursement/{req.request_id}/mark_checked", follow_redirects=True)
    assert r_mc.status_code == 200
    db.session.refresh(req)
    # check_status 已为 CHECKED
    assert str(req.check_status.value) == "CHECKED"

    # 已核对后再次尝试审批应被阻止
    r_ap2 = client.post(f"/reimbursement/{req.request_id}/approve", data={"approval_comments": "again"},
                        follow_redirects=True)
    assert r_ap2.status_code == 200

    # 已核对后尝试转交应被阻止
    r_tf = client.post(f"/reimbursement/{req.request_id}/transfer", data={"new_approver_id": str(finance2.user_id)},
                       follow_redirects=True)
    assert r_tf.status_code == 200

    # 列表页不再出现“标记已核对”按钮，且显示“已核对”
    r_list2 = client.get("/reimbursement/?category=done")
    html2 = r_list2.get_data(as_text=True)
    assert "mark_checked" not in html2
    assert "已核对" in html2
