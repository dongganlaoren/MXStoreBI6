def test_root_requires_login_redirects_to_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307, 308)
    location = resp.headers.get("Location", "")
    # Flask-Login usually appends ?next=%2F
    assert "/login" in location


def test_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"\xe7\x99\xbb\xe5\xbd\x95" in resp.data  # 包含“登录”字样


def test_root_redirect_when_logged_in(client, admin_user):
    # 登录
    client.post("/login", data={"username": "admin", "password": "secret123"}, follow_redirects=True)
    # 访问根路径
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (301, 302, 303, 307, 308)
    assert "/" in r.headers.get("Location", "")
