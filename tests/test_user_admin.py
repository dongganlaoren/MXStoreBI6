import pytest
from flask import url_for
from app import create_app, db
from app.models import User, RoleType

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False  # 测试禁用CSRF
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # 创建一个管理员用户
            admin = User(username='admin', role=RoleType.ADMIN)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def login(client, username, password):
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def test_admin_user_list(client):
    login(client, 'admin', 'admin123')
    resp = client.get('/admin/users/')
    assert b'用户管理' in resp.data

def test_admin_create_user(client):
    login(client, 'admin', 'admin123')
    resp = client.post('/admin/users/create', data={
        'username': 'testuser',
        'password': 'test1234',
        'confirm_password': 'test1234',
        'role': RoleType.EMPLOYEE.value,
        'store_id': ''
    }, follow_redirects=True)
    assert b'用户管理' in resp.data
    assert b'testuser' in resp.data

def test_admin_edit_user(client):
    login(client, 'admin', 'admin123')
    # 创建用户
    user = User(username='edituser', role=RoleType.EMPLOYEE)
    user.set_password('edit1234')
    db.session.add(user)
    db.session.commit()
    # 编辑
    resp = client.post(f'/admin/users/{user.user_id}/edit', data={
        'real_name': '新名字',
        'phone': '123456',
        'email': 'a@b.com',
        'store_id': ''
    }, follow_redirects=True)
    assert b'新名字' in resp.data

def test_admin_delete_user(client):
    login(client, 'admin', 'admin123')
    user = User(username='deluser', role=RoleType.EMPLOYEE)
    user.set_password('del1234')
    db.session.add(user)
    db.session.commit()
    resp = client.post(f'/admin/users/{user.user_id}/delete', follow_redirects=True)
    assert b'deluser' not in resp.data
