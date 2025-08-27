from io import BytesIO

from app.models.enums import RoleType


def test_register_admin_login_auto(client, db_session):
    resp = client.get("/register")
    assert resp.status_code == 200
    r = client.post(
        "/register",
        data={
            "username": "newadmin",
            "password": "secret123",
            "confirm_password": "secret123",
            "role": RoleType.ADMIN.value,
            "store_id": "",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    # 登录后访问 /profile
    p = client.get("/profile")
    assert p.status_code == 200


def test_edit_profile_basic(client, admin_user, login):
    # 登录现有管理员
    resp = login("admin", "secret123")
    assert resp.status_code == 200

    # GET 个人资料
    r1 = client.get("/profile")
    assert r1.status_code == 200

    # POST 编辑资料（提供必填字段）
    r2 = client.post(
        "/profile/edit",
        data={
            "real_name": "Admin",
            "employee_number": "",
            "role": RoleType.ADMIN.value,
            "store_id": "",
            "email": "",
        },
        follow_redirects=True,
    )
    assert r2.status_code == 200


def test_login_failure_and_logout_and_download_id_copy(client, admin_user, login):
    # 登录失败
    r0 = client.post("/login", data={"username": "nope", "password": "bad"}, follow_redirects=True)
    assert r0.status_code == 200

    # 登录成功
    resp = login("admin", "secret123")
    assert resp.status_code == 200

    # 未上传身份证复印件时访问下载接口应404
    r1 = client.get("/download_id_card_copy")
    assert r1.status_code == 404

    # 通过编辑资料上传身份证复印件
    data = {
        "real_name": "Admin",
        "employee_number": "",
        "role": RoleType.ADMIN.value,
        "store_id": "",
        "email": "",
        "id_card_copy": (BytesIO(b"fake-data"), "id.png"),
    }
    r2 = client.post("/profile/edit", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert r2.status_code == 200

    # 现在下载应成功且为在线预览
    r3 = client.get("/download_id_card_copy")
    assert r3.status_code == 200
    cd = r3.headers.get("Content-Disposition", "")
    assert "attachment" not in cd.lower()

    # 登出
    r4 = client.get("/logout", follow_redirects=True)
    assert r4.status_code == 200
