from datetime import date, timedelta

from app.extensions import db
from app.models import User, Store, DailySales
from app.models.enums import RoleType, FinancialCheckStatus


def test_user_login_redirect_when_authenticated(client, admin_user):
    # 先登录
    client.post('/login', data={'username': 'admin', 'password': 'secret123'}, follow_redirects=True)
    # 已登录访问 /login 应重定向到首页
    r = client.get('/login', follow_redirects=False)
    assert r.status_code in (301, 302, 303, 307, 308)


def test_user_register_redirect_when_authenticated(client, admin_user):
    client.post('/login', data={'username': 'admin', 'password': 'secret123'}, follow_redirects=True)
    r = client.get('/register', follow_redirects=False)
    assert r.status_code in (301, 302, 303, 307, 308)


def test_user_staff_view_page(client, admin_user, login):
    login('admin', 'secret123')
    r = client.get('/staff/view?lang=zh')
    assert r.status_code == 200


def test_admin_user_list_filter_q(client, admin_user, login):
    # 新增两个用户，便于搜索过滤
    u1 = User(username='query_foo', role=RoleType.EMPLOYEE, user_status=1)
    u1.set_password('x')
    u2 = User(username='bar', role=RoleType.EMPLOYEE, user_status=1)
    u2.set_password('x')
    db.session.add_all([u1, u2])
    db.session.commit()

    login('admin', 'secret123')
    r = client.get('/admin/users/?q=query_')
    assert r.status_code == 200


def test_main_index_for_branch_manager_with_store(client, db_session):
    # 建门店
    s = Store(store_id='B001', store_name='Branch 1')
    db.session.add(s)
    db.session.commit()
    # 创建分店长并关联门店
    bm = User(username='bm2', role=RoleType.BRANCH_MANAGER, user_status=1, store_id=s.store_id)
    bm.set_password('pw')
    db.session.add(bm)
    db.session.commit()
    # 在近一年内插入一条含 takeaway 的 APPROVED 数据，触发 has_t1 分支
    db.session.add(DailySales(
        store_id=s.store_id,
        user_id=bm.user_id,
        report_date=date.today(),
        pos_total=100.0,
        takeaway_amount=10.0,
        actual_sales=90.0,
        total_error=0.0,
        financial_check_status=FinancialCheckStatus.APPROVED,
    ))
    # 近一周插入一天 APPROVED 数据用于日报列表
    db.session.add(DailySales(
        store_id=s.store_id,
        user_id=bm.user_id,
        report_date=date.today() - timedelta(days=1),
        pos_total=50.0,
        takeaway_amount=0.0,
        actual_sales=50.0,
        total_error=0.0,
        financial_check_status=FinancialCheckStatus.APPROVED,
    ))
    db.session.commit()

    # 登录并访问首页
    client.post('/login', data={'username': 'bm2', 'password': 'pw'}, follow_redirects=True)
    r = client.get('/', follow_redirects=True)
    assert r.status_code == 200


def test_main_index_exception_branch(client, admin_user, login, monkeypatch):
    # 登录管理员
    login('admin', 'secret123')

    # monkeypatch Store.query.order_by 以抛出异常
    import app.views.main_views as mv

    class _Q:
        def order_by(self, *a, **k):
            raise RuntimeError('boom')

    class _DummyStore:
        query = _Q()

    monkeypatch.setattr(mv, 'Store', _DummyStore)

    r = client.get('/', follow_redirects=True)
    # 异常被捕获并渲染空页面
    assert r.status_code == 200
