import importlib
import os
import sys

import pytest
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.extensions import db as _db
from app.models import User
from app.models.enums import RoleType


class TestConfig:
    TESTING = True
    DEBUG = True
    ENV = 'testing'
    SECRET_KEY = 'test_secret_key'
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep a single in-memory SQLite DB across connections
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
        'poolclass': StaticPool,
    }
    # Minimal mail config to satisfy Flask-Mail init
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_SUPPRESS_SEND = True


@pytest.fixture(scope='session')
def app():
    flask_app = create_app(TestConfig)

    # Ensure models are imported so tables exist without rebinding name 'app'
    importlib.import_module('app.models')

    with flask_app.app_context():
        _db.create_all()
    yield flask_app

    # Teardown: drop tables
    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()
        # 显式释放底层连接，避免 ResourceWarning
        try:
            _db.engine.dispose()
        except Exception:
            pass


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide a clean database session per test (transactional)."""
    with app.app_context():
        connection = _db.engine.connect()
        trans = connection.begin()
        Session = scoped_session(sessionmaker(bind=connection))
        old_session = _db.session
        _db.session = Session
        try:
            yield Session
        finally:
            # rollback to savepoint and restore session
            Session.remove()
            trans.rollback()
            connection.close()
            _db.session = old_session


@pytest.fixture()
def admin_user(db_session):
    u = User(username="admin", role=RoleType.ADMIN, user_status=1)
    u.set_password("secret123")
    _db.session.add(u)
    _db.session.commit()
    return u


@pytest.fixture()
def login(client):
    def _login(username: str, password: str):
        return client.post(
            "/login",
            data={"username": username, "password": password, "remember_me": "y"},
            follow_redirects=True,
        )

    return _login


# 供其他测试文件复用的基础夹具（与财务报销用例一致）
@pytest.fixture()
def store_r(db_session):
    from app.models import Store
    s = Store(store_id="RS1", store_name="Reimb Store")
    _db.session.add(s)
    _db.session.commit()
    return s


@pytest.fixture()
def submitter(db_session, store_r):
    from app.models import User
    from app.models.enums import RoleType
    u = User(username="bm1", role=RoleType.EMPLOYEE, user_status=1, store_id=store_r.store_id, email="bm1@ex.com")
    u.set_password("pw")
    _db.session.add(u)
    _db.session.commit()
    return u


@pytest.fixture()
def finance1(db_session):
    from app.models import User
    from app.models.enums import RoleType
    u = User(username="fin1", role=RoleType.FINANCE, user_status=1, email="fin1@ex.com")
    u.set_password("pw")
    _db.session.add(u)
    _db.session.commit()
    return u
