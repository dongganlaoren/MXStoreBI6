import pytest
from flask import url_for
from app import create_app, db
from app.models import User, RoleType

# 新增：统一的用户创建工具函数
def create_user(username, role=RoleType.EMPLOYEE, password='test1234', **kwargs):
    user = User(username=username, role=role, **kwargs)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False  # 测试禁用CSRF
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # 创建一个管理员用户
            create_user('admin', role=RoleType.ADMIN, password='admin123')
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
    # 创建用户（使用工具函数）
    user = create_user('edituser', role=RoleType.EMPLOYEE, password='edit1234')
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
    user = create_user('deluser', role=RoleType.EMPLOYEE, password='del1234')
    resp = client.post(f'/admin/users/{user.user_id}/delete', follow_redirects=True)
    assert b'deluser' not in resp.data
