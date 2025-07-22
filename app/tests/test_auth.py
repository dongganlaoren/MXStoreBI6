import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import pytest
from flask import url_for
from app import create_app, db
from app.models.user import User
from config import TestingConfig

@pytest.fixture
def client():
    app = create_app(TestingConfig)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # 创建一个测试用户
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def test_login_success(client):
    response = client.post('/user/login', data={
        'username': 'testuser',
        'password': 'testpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert '登出' in response.get_data(as_text=True) or 'logout' in response.get_data(as_text=True)

def test_login_fail(client):
    response = client.post('/user/login', data={
        'username': 'testuser',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert '用户名或密码无效' in response.get_data(as_text=True) or '登录' in response.get_data(as_text=True)

def test_register(client):
    response = client.post('/user/register', data={
        'username': 'newuser',
        'password': 'newpass',
        'confirm_password': 'newpass',
        'role': 'ADMIN'
    }, follow_redirects=True)
    assert response.status_code == 200
    with client.application.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.username == 'newuser'
