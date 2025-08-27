import pytest

from app.extensions import db
from app.models import User
from app.models.enums import RoleType


@pytest.fixture()
def user_admin(db_session):
    u = User(username="admin", role=RoleType.ADMIN, user_status=1)
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    return u


def test_login_success_and_access_index(client, user_admin):
    # 登录
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "secret123", "remember_me": "y"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # 登录后访问首页应为 200
    resp2 = client.get("/", follow_redirects=True)
    assert resp2.status_code == 200
    assert b"\xe6\x97\xa0\xe5\xba\x97\xe9\x93\xba\xe6\x95\xb0\xe6\x8d\xae" in resp2.data  # “暂无店铺数据” 提示


def test_login_fail_shows_flash(client):
    resp = client.post(
        "/login",
        data={"username": "nope", "password": "bad"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # 含有“用户名或密码无效”提示
    assert b"\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81\xe6\x97\xa0\xe6\x95\x88" in resp.data
