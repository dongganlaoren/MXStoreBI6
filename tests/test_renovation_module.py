# tests/test_renovation_module.py
from datetime import datetime, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models.enums import RoleType, RenovationTaskStatus, RenovationTaskPriority, RenovationTaskCategory, \
    VerificationResult
from app.models.renovation import RenovationTask
from app.models.store import Store
from app.models.user import User
from config import TestingConfig  # ���正：TestConfig -> TestingConfig


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(TestingConfig)  # 修正：TestConfig -> TestingConfig
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """创建已认证的测试客户端"""
    with app.app_context():
        # 创建测试店铺
        store = Store(store_id="TEST001", store_name="测试店铺")
        db.session.add(store)

        # 创建管理员用户
        admin_user = User(
            username="admin",
            employee_number="ADMIN001",
            role=RoleType.ADMIN,
            real_name="管理员",
            email="admin@test.com"
        )
        admin_user.set_password("password")
        db.session.add(admin_user)

        # 创建店长用户
        manager_user = User(
            username="manager",
            employee_number="MGR001",
            role=RoleType.BRANCH_MANAGER,
            store_id="TEST001",
            real_name="店长",
            email="manager@test.com"
        )
        manager_user.set_password("password")
        db.session.add(manager_user)

        db.session.commit()

        # 强制设置测试认证：cookie + session，保证测试客户端有登录状态
        try:
            client.set_cookie('localhost', 'TEST_AUTH', 'admin')
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin_user.user_id)
                sess['_fresh'] = True
        except Exception:
            pass

        # 登录管理员
        response = client.post('/user/login', data={
            'username': 'admin',
            'password': 'password'
        })
        print(f"Login response status: {response.status_code}")
        print(f"Login response data: {response.get_data(as_text=True)}")

        # 验证登录状态
        with client.session_transaction() as sess:
            print(f"Session after login: {dict(sess)}")

        return client


class TestRenovationModule:
    """店铺整改模块测试类"""

    def test_renovation_list_page(self, auth_client):
        """测试整改任务列表页面"""
        response = auth_client.get('/renovation/')
        assert response.status_code == 200
        assert '整改任务列表' in response.get_data(as_text=True)

    def test_create_renovation_task(self, auth_client, app):
        """测试创建整改任务"""
        with app.app_context():
            # 准备测试数据
            due_date = datetime.utcnow() + timedelta(days=7)

            response = auth_client.post('/renovation/create', data={
                'title': '测试整改任务',
                'description': '这是一个测试的整改任务描述',
                'category': 'HYGIENE',
                'priority': 'HIGH',
                'store_id': 'TEST001',
                'due_date': due_date.strftime('%Y-%m-%dT%H:%M'),
                'csrf_token': 'test'  # 在测试中可能需要处理CSRF
            }, follow_redirects=True)

            # 验证任务创���成���
            task = RenovationTask.query.filter_by(title='测试整改任务').first()
            assert task is not None
            assert task.description == '这是一个测试的整改任务描述'
            assert task.priority == RenovationTaskPriority.HIGH
            assert task.store_id == 'TEST001'

    def test_task_workflow(self, auth_client, app):
        """测试完整的任务流程"""
        with app.app_context():
            # 1. 创建任务
            admin_user = User.query.filter_by(username='admin').first()
            manager_user = User.query.filter_by(username='manager').first()

            task = RenovationTask(
                title='流程��试任务',
                description='测试完整流程',
                priority=RenovationTaskPriority.URGENT,
                store_id='TEST001',
                created_by=admin_user.user_id,  # 修正：使用 user_id
                assigned_to=manager_user.user_id,  # 修正：���用 user_id
                verifier_id=admin_user.user_id,  # 修正：使用 user_id
                due_date=datetime.utcnow() + timedelta(days=3)
            )
            db.session.add(task)
            db.session.commit()

            # 2. 验证任务状态
            assert task.status == RenovationTaskStatus.PENDING

            # 3. 模拟店长处理任务
            task.status = RenovationTaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            db.session.commit()

            # 4. 模拟完成任务
            task.status = RenovationTaskStatus.AWAITING_VERIFICATION
            task.completed_at = datetime.utcnow()
            db.session.commit()

            # 5. 模拟验收
            task.verification_result = VerificationResult.PASSED
            task.verification_comments = '验收通过'
            task.status = RenovationTaskStatus.COMPLETED
            task.verified_at = datetime.utcnow()
            db.session.commit()

            # 验证最终状态
            assert task.status == RenovationTaskStatus.COMPLETED
            assert task.verification_result == VerificationResult.PASSED

    def test_task_permissions(self, auth_client, app):
        """测试任务权限控制"""
        with app.app_context():
            # 创建一个任务
            admin_user = User.query.filter_by(username='admin').first()
            manager_user = User.query.filter_by(username='manager').first()

            task = RenovationTask(
                title='权限测试任务',
                description='测试权限控制',
                priority=RenovationTaskPriority.MEDIUM,
                store_id='TEST001',
                created_by=admin_user.user_id,  # 修正：使用 user_id
                assigned_to=manager_user.user_id,  # 修正：使用 user_id
                verifier_id=admin_user.user_id,  # 修正：使用 user_id
                due_date=datetime.utcnow() + timedelta(days=5)
            )
            db.session.add(task)
            db.session.commit()

            # 管理员应该能看到任务详情
            response = auth_client.get(f'/renovation/detail/{task.id}')
            assert response.status_code == 200

    def test_task_filtering(self, auth_client, app):
        """测试任务筛选功能"""
        with app.app_context():
            admin_user = User.query.filter_by(username='admin').first()
            manager_user = User.query.filter_by(username='manager').first()

            # 创建不同状态的任务
            tasks = [
                RenovationTask(
                    title=f'任务{i}',
                    description=f'描述{i}',
                    priority=RenovationTaskPriority.HIGH if i % 2 == 0 else RenovationTaskPriority.LOW,
                    status=RenovationTaskStatus.PENDING if i < 2 else RenovationTaskStatus.COMPLETED,
                    store_id='TEST001',
                    created_by=admin_user.user_id,  # 修正：使用 user_id
                    assigned_to=manager_user.user_id,  # 修正：使用 user_id
                    verifier_id=admin_user.user_id,  # 修正：使用 user_id
                    due_date=datetime.utcnow() + timedelta(days=i + 1)
                ) for i in range(4)
            ]

            for task in tasks:
                db.session.add(task)
            db.session.commit()

            # 测试按状态筛选
            response = auth_client.get('/renovation/?status=PENDING')
            assert response.status_code == 200

            # 测试按优先级筛选
            response = auth_client.get('/renovation/?priority=HIGH')
            assert response.status_code == 200

    def test_overdue_detection(self, app):
        """测试逾期检测功能"""
        with app.app_context():
            # 创建测试用户
            store = Store(store_id="TEST001", store_name="测试店铺")
            db.session.add(store)

            admin_user = User(
                username="admin",
                employee_number="ADMIN001",
                role=RoleType.ADMIN,
                real_name="管理员"
            )
            admin_user.set_password("password")
            db.session.add(admin_user)

            manager_user = User(
                username="manager",
                employee_number="MGR001",
                role=RoleType.BRANCH_MANAGER,
                store_id="TEST001",
                real_name="店长"
            )
            manager_user.set_password("password")
            db.session.add(manager_user)

            db.session.commit()

            # 创建逾期任务
            overdue_task = RenovationTask(
                title='逾期任务',
                description='测试逾期检测',
                priority=RenovationTaskPriority.URGENT,
                store_id='TEST001',
                created_by=admin_user.user_id,  # 修正：使用 user_id
                assigned_to=manager_user.user_id,  # 修正：使用 user_id
                verifier_id=admin_user.user_id,  # 修正：使用 user_id
                due_date=datetime.utcnow() - timedelta(days=1)  # 昨天到期
            )
            db.session.add(overdue_task)
            db.session.commit()

            # 验证逾期检测
            assert overdue_task.is_overdue is True
            assert overdue_task.days_remaining == 0

    def test_statistics_calculation(self, app):
        """测试统计功能"""
        with app.app_context():
            # 创建测试用户
            store = Store(store_id="TEST001", store_name="测试店铺")
            db.session.add(store)

            admin_user = User(
                username="admin",
                employee_number="ADMIN001",
                role=RoleType.ADMIN,
                real_name="管理员"
            )
            admin_user.set_password("password")
            db.session.add(admin_user)

            manager_user = User(
                username="manager",
                employee_number="MGR001",
                role=RoleType.BRANCH_MANAGER,
                store_id="TEST001",
                real_name="店长"
            )
            manager_user.set_password("password")
            db.session.add(manager_user)

            db.session.commit()

            # 创建多个任务用于统计
            for i in range(10):
                status = RenovationTaskStatus.COMPLETED if i < 7 else RenovationTaskStatus.PENDING
                task = RenovationTask(
                    title=f'统计任务{i}',
                    description=f'统计描述{i}',
                    priority=RenovationTaskPriority.MEDIUM,
                    status=status,
                    store_id='TEST001',
                    created_by=admin_user.user_id,  # 修正：使用 user_id
                    assigned_to=manager_user.user_id,  # 修正：使用 user_id
                    verifier_id=admin_user.user_id,  # 修正：使用 user_id
                    due_date=datetime.utcnow() + timedelta(days=i + 1)
                )
                db.session.add(task)

            db.session.commit()

            # 计算统计数据
            total_tasks = RenovationTask.query.count()
            completed_tasks = RenovationTask.query.filter_by(status=RenovationTaskStatus.COMPLETED).count()
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            assert total_tasks == 10
            assert completed_tasks == 7
            assert completion_rate == 70.0

    def test_language_support(self, auth_client):
        """测试中泰双语支持"""
        # 测试中文
        response = auth_client.get('/renovation/?lang=zh')
        assert response.status_code == 200

        # 测试泰文
        response = auth_client.get('/renovation/?lang=th')
        assert response.status_code == 200


def test_renovation_models():
    """测试数据模型"""
    # 测试枚举值
    assert RenovationTaskStatus.PENDING.value == 'PENDING'
    assert RenovationTaskPriority.URGENT.value == 'URGENT'
    assert RenovationTaskCategory.HYGIENE.value == 'HYGIENE'
    assert VerificationResult.PASSED.value == 'PASSED'


if __name__ == '__main__':
    pytest.main([__file__])
