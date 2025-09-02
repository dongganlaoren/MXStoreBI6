# 损益报表功能测试用例

from datetime import datetime, date, timedelta
from decimal import Decimal

import pytest

from app import create_app, db
from app.models import User, Store, DailySales, ReimbursementRequest
from app.models.enums import (
    RoleType, FinancialCheckStatus, ReimbursementStatus,
    ReimbursementPrimaryCategory, ReimbursementSecondaryCategory
)
from config import TestingConfig


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(TestingConfig)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_admin(client, app):
    """创建管理员用户并登录"""
    with app.app_context():
        admin = User(
            username='admin',
            email='admin@test.com',
            role=RoleType.ADMIN
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        # 登录
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })

        return admin


@pytest.fixture
def test_stores(app):
    """创建测试门店数据"""
    with app.app_context():
        stores = [
            Store(store_id='S001', store_name='测试门店1'),
            Store(store_id='S002', store_name='测试门店2'),
            Store(store_id='S003', store_name='测试门店3')
        ]
        for store in stores:
            db.session.add(store)
        db.session.commit()
        return stores


@pytest.fixture
def test_sales_data(app, test_stores):
    """创建测试销售数据"""
    with app.app_context():
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)

        sales_data = [
            # ��店1 - 高收入
            DailySales(
                store_id='S001',
                user_id=1,
                report_date=last_month,
                actual_sales=50000.0,
                financial_check_status=FinancialCheckStatus.APPROVED
            ),
            # 门店2 - 中等收入
            DailySales(
                store_id='S002',
                user_id=1,
                report_date=last_month,
                actual_sales=30000.0,
                financial_check_status=FinancialCheckStatus.APPROVED
            ),
            # 门店3 - 低收入
            DailySales(
                store_id='S003',
                user_id=1,
                report_date=last_month,
                actual_sales=20000.0,
                financial_check_status=FinancialCheckStatus.APPROVED
            )
        ]

        for sales in sales_data:
            db.session.add(sales)
        db.session.commit()
        return sales_data


@pytest.fixture
def test_cost_data(app, test_stores):
    """创建测试成本数据"""
    with app.app_context():
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)
        approved_time = datetime.combine(last_month, datetime.min.time())

        cost_data = [
            # 门店1成本
            ReimbursementRequest(
                submitter_id=1,
                store_id='S001',
                primary_category=ReimbursementPrimaryCategory.STORE_COST,
                secondary_category=ReimbursementSecondaryCategory.STORE_RENT,
                amount=Decimal('15000.00'),
                status=ReimbursementStatus.APPROVED,
                approved_at=approved_time,
                approver_id=1
            ),
            ReimbursementRequest(
                submitter_id=1,
                store_id='S001',
                primary_category=ReimbursementPrimaryCategory.STORE_COST,
                secondary_category=ReimbursementSecondaryCategory.UTILITIES,
                amount=Decimal('5000.00'),
                status=ReimbursementStatus.APPROVED,
                approved_at=approved_time,
                approver_id=1
            ),
            # 门店2成本
            ReimbursementRequest(
                submitter_id=1,
                store_id='S002',
                primary_category=ReimbursementPrimaryCategory.STORE_COST,
                secondary_category=ReimbursementSecondaryCategory.STORE_RENT,
                amount=Decimal('12000.00'),
                status=ReimbursementStatus.APPROVED,
                approved_at=approved_time,
                approver_id=1
            ),
            # 门店3成本 - 高成本，可能亏损
            ReimbursementRequest(
                submitter_id=1,
                store_id='S003',
                primary_category=ReimbursementPrimaryCategory.STORE_COST,
                secondary_category=ReimbursementSecondaryCategory.STORE_RENT,
                amount=Decimal('25000.00'),
                status=ReimbursementStatus.APPROVED,
                approved_at=approved_time,
                approver_id=1
            )
        ]

        for cost in cost_data:
            db.session.add(cost)
        db.session.commit()
        return cost_data


class TestProfitLossReports:
    """损益报表功能测试类"""

    def test_profit_loss_reports_access_control(self, client, app):
        """测试损益报表访问权限控制"""
        with app.app_context():
            # 测试未登录用户
            response = client.get('/profit_loss_reports')
            assert response.status_code == 302  # 重定向到登录页

            # 创建并登录普通用户（店长）
            store_manager = User(
                username='manager',
                email='manager@test.com',
                role=RoleType.BRANCH_MANAGER
            )
            store_manager.set_password('manager123')
            db.session.add(store_manager)
            db.session.commit()

            client.post('/login', data={
                'username': 'manager',
                'password': 'manager123'
            })

            # 店长应该无权访问
            response = client.get('/profit_loss_reports')
            assert response.status_code == 302

            # 登出
            client.get('/logout')

    def test_profit_loss_reports_admin_access(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试管理员可以正常访问损益报表"""
        response = client.get('/profit_loss_reports')
        assert response.status_code == 200
        assert '损益报表' in response.get_data(as_text=True)
        assert '总收入' in response.get_data(as_text=True)
        assert '总成本' in response.get_data(as_text=True)
        assert '净利润' in response.get_data(as_text=True)

    def test_profit_loss_calculation(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试损益计算的正确性"""
        response = client.get('/profit_loss_reports')
        data = response.get_data(as_text=True)

        # 验证总收入：50000 + 30000 + 20000 = 100000
        assert '100,000.00' in data

        # 验证总成本：20000 + 12000 + 25000 = 57000
        assert '57,000.00' in data

        # 验证总利润：100000 - 57000 = 43000
        assert '43,000.00' in data

        # 验证各门店盈亏状态
        assert '测试门店1' in data  # 盈利门店
        assert '测试门店2' in data  # 盈利门店
        assert '测试门店3' in data  # 亏损门店（收入20000，成本25000）

    def test_profit_loss_store_filter(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试按门店筛选功能"""
        # 筛选门店1
        response = client.get('/profit_loss_reports?store_id=S001')
        data = response.get_data(as_text=True)

        # 应该只显示门店1的数据
        assert '测试门店1' in data
        assert '50,000.00' in data  # 门店1收入
        assert '20,000.00' in data  # 门店1成本

        # 不应该显示其他门店数据
        assert '测试门店2' not in data
        assert '测试门店3' not in data

    def test_profit_loss_date_filter(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试按日期筛选功能"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 筛选昨天的数据（应该没有数据）
        response = client.get(f'/profit_loss_reports?start_date={yesterday}&end_date={yesterday}')
        data = response.get_data(as_text=True)

        # 总计应该为0
        assert '0.00' in data

    def test_profit_margin_calculation(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试利润率计算"""
        response = client.get('/profit_loss_reports')
        data = response.get_data(as_text=True)

        # 门店1：利润率 = (50000-20000)/50000 * 100 = 60%
        # 门店2：利润率 = (30000-12000)/30000 * 100 = 60%
        # 门店3：利润率 = (20000-25000)/20000 * 100 = -25%
        # 整体利润率 = (100000-57000)/100000 * 100 = 43%

        assert '60.00%' in data  # 门店1和门店2的利润率
        assert '-25.00%' in data  # 门店3的负利润率
        assert '43.00%' in data  # 整体利润率

    def test_profit_loss_sorting(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试损益报表按利润排序"""
        response = client.get('/profit_loss_reports')
        data = response.get_data(as_text=True)

        # 验证排序：门店1利润最高(30000)，门店2次之(18000)，门店3最低(-5000)
        # 在HTML中，排名应该按利润降序显示
        assert data.index('测试门店1') < data.index('测试门店2')
        assert data.index('测试门店2') < data.index('测试门店3')

    def test_cost_category_breakdown(self, client, auth_admin, test_stores, test_sales_data, test_cost_data):
        """测试成本分类统计"""
        response = client.get('/profit_loss_reports')
        data = response.get_data(as_text=True)

        # 验证成本分类数据存在
        assert 'costCategoryChart' in data  # 饼图容器
        # 只验证图表容器存在，不检查具体的枚举值显示
        assert 'categories' in data  # JavaScript中的categories数据

    def test_profit_loss_financial_user(self, client, app, test_stores, test_sales_data, test_cost_data):
        """测试财务用户可以访问损益报表"""
        with app.app_context():
            # 创建财务用户
            finance_user = User(
                username='finance',
                email='finance@test.com',
                role=RoleType.FINANCE
            )
            finance_user.set_password('finance123')
            db.session.add(finance_user)
            db.session.commit()

            # 登录财务用户
            client.post('/login', data={
                'username': 'finance',
                'password': 'finance123'
            })

            # 应该可以正常访问
            response = client.get('/profit_loss_reports')
            assert response.status_code == 200
            assert '损益报表' in response.get_data(as_text=True)

    def test_empty_data_handling(self, client, auth_admin, test_stores):
        """测试无数据情况的处理"""
        # 没有销售和成本数据时
        response = client.get('/profit_loss_reports')
        data = response.get_data(as_text=True)

        # 应该显示0值
        assert '0.00' in data
        assert '0家门店' in data

    def test_menu_navigation(self, client, auth_admin):
        """测试菜单导航链接"""
        # 访问主页，检查是否有损益报表菜单
        response = client.get('/home')  # 使用/home而不是/
        data = response.get_data(as_text=True)

        # 检查报表中心下拉菜单中是否有损益报表选项
        assert 'profit_loss_reports' in data or '损益报表' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
