from app.extensions import db
from app.models import User
from app.models.enums import RoleType


def test_admin_user_list_requires_admin(client, admin_user, login):
    # 登录管理员
    resp = login("admin", "secret123")
    assert resp.status_code == 200
    # 访问用户列表
    r = client.get("/admin/users/", follow_redirects=True)
    assert r.status_code == 200
    # 页面包含列表模板的关键元素
    assert b"user_list" in r.data or b"\xe7\x94\xa8\xe6\x88\xb7" in r.data


def test_admin_user_detail_edit_and_delete(client, admin_user, login):
    # 先创建一个普通用户
    u = User(username="bob", role=RoleType.EMPLOYEE, user_status=1)
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()

    # 登录管理员
    resp = login("admin", "secret123")
    assert resp.status_code == 200

    # 详情页
    r = client.get(f"/admin/users/{u.user_id}")
    assert r.status_code == 200

    # 编辑（仅修改 role 为 ADMIN）
    r2 = client.post(
        f"/admin/users/{u.user_id}/edit",
        data={
            "real_name": "",
            "employee_number": "",
            "role": RoleType.ADMIN.value,
            "store_id": "",
        },
        follow_redirects=True,
    )
    assert r2.status_code == 200

    # 删除
    r3 = client.post(f"/admin/users/{u.user_id}/delete", follow_redirects=True)
    assert r3.status_code == 200
    assert User.query.filter_by(username="bob").first() is None


def test_admin_user_create_and_reset_password(client, admin_user, login):
    # 登录管理员
    resp = login("admin", "secret123")
    assert resp.status_code == 200

    # 创建新用户（管理组，无需店铺）
    r = client.post(
        "/admin/users/create",
        data={
            "username": "alice",
            "password": "secret123",
            "confirm_password": "secret123",
            "role": RoleType.ADMIN.value,
            "store_id": "",
            "real_name": "",
            "email": "",
            "phone": "",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    alice = User.query.filter_by(username="alice").first()
    assert alice is not None

    # 重置密码端点
    r2 = client.post(f"/admin/users/{alice.user_id}/reset_password", follow_redirects=True)
    assert r2.status_code == 200
