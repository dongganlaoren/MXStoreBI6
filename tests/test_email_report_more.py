from datetime import date

from app.extensions import db
from app.models import User
from app.models.email_task_log import EmailTaskLog, EmailTaskType, EmailTaskStatus
from app.models.enums import RoleType
from app.views.email_report_views import register_email_report_tasks, send_report_task


class _FakeScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, func, trigger, id, replace_existing):
        # 只记录关键信息，避免实例化触发
        self.jobs.append({
            'id': id,
            'replace_existing': replace_existing,
            'trigger': type(trigger).__name__,
            'func': func,
        })


def test_register_email_report_tasks_registers_jobs(app):
    fake = _FakeScheduler()
    # 直接调用注册函数
    register_email_report_tasks(fake, app)
    ids = {j['id'] for j in fake.jobs}
    assert ids == {
        'branch_manager_daily_report',
        'admin_finance_daily_report',
        'branch_manager_weekly_report',
        'admin_finance_weekly_report',
        'branch_manager_monthly_report',
        'admin_finance_monthly_report',
    }


def _make_users(role: RoleType, n: int = 3):
    users = []
    for i in range(n):
        u = User(username=f"u_{role.name}_{i}", role=role, user_status=1, email=f"{role.name.lower()}{i}@ex.com")
        u.set_password("x")
        db.session.add(u)
        users.append(u)
    db.session.commit()
    return users


def test_send_report_task_status_success(app, db_session, monkeypatch):
    _make_users(RoleType.ADMIN, 2)
    # 全成功
    monkeypatch.setattr("app.views.email_report_views.send_sales_report_mail", lambda *a, **k: True)
    with app.app_context():
        send_report_task('day', RoleType.ADMIN, app)
        log = EmailTaskLog.query.order_by(EmailTaskLog.id.desc()).first()
        assert log is not None
        assert log.task_type == EmailTaskType.daily
        assert log.status == EmailTaskStatus.success
        assert log.success_count >= 1 and log.fail_count == 0


def test_send_report_task_status_partial_fail(app, db_session, monkeypatch):
    _make_users(RoleType.FINANCE, 3)

    # 部分失败：返回序列 True, False, True
    seq = iter([True, False, True])

    def _send(*a, **k):
        try:
            return next(seq)
        except StopIteration:
            return True

    monkeypatch.setattr("app.views.email_report_views.send_sales_report_mail", _send)

    with app.app_context():
        send_report_task('week', RoleType.FINANCE, app)
        log = EmailTaskLog.query.order_by(EmailTaskLog.id.desc()).first()
        assert log.task_type == EmailTaskType.weekly
        assert log.status == EmailTaskStatus.partial_fail
        assert log.success_count >= 1 and log.fail_count >= 1


def test_send_report_task_status_fail(app, db_session, monkeypatch):
    _make_users(RoleType.HEAD_MANAGER, 2)
    monkeypatch.setattr("app.views.email_report_views.send_sales_report_mail", lambda *a, **k: False)
    with app.app_context():
        send_report_task('month', RoleType.HEAD_MANAGER, app)
        log = EmailTaskLog.query.order_by(EmailTaskLog.id.desc()).first()
        assert log.task_type == EmailTaskType.monthly
        assert log.status == EmailTaskStatus.fail
        assert log.success_count == 0 and log.fail_count >= 1


def test_email_report_log_list_page(client, db_session):
    # 预置一条日志，确保页面有数据
    db.session.add(EmailTaskLog(
        task_type=EmailTaskType.daily,
        start_date=date.today(),
        end_date=date.today(),
        recipients='a@ex.com,b@ex.com',
        status=EmailTaskStatus.success,
        success_count=2,
        fail_count=0
    ))
    db.session.commit()

    r = client.get('/email_report/log_list')
    assert r.status_code == 200
