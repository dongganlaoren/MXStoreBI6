"""
自动生成门店、用户、日报、财务报销申请测试数据，严格符合模型字段定义。
"""
import random
from datetime import datetime, timedelta, date

from faker import Faker
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Store, User, DailySales
from app.models.enums import ReimbursementPrimaryCategory, ReimbursementSecondaryCategory, ReimbursementStatus
from app.models.enums import RoleType, FinancialCheckStatus
from app.models.reimbursement import ReimbursementRequest

fake = Faker("zh_CN")


def generate_fake_data():
    try:
        # 清空所有业务表（排除 alembic_version）
        with db.session.begin_nested():
            table_names = db.inspect(db.engine).get_table_names()
            db_url = db.engine.url.drivername
            if 'sqlite' in db_url:
                db.session.execute(text('PRAGMA foreign_keys = OFF'))
            elif 'mysql' in db_url:
                db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))
            for table in table_names:
                if table == "alembic_version":
                    continue
                db.session.execute(text(f'DELETE FROM {table}'))
            if 'sqlite' in db_url:
                db.session.execute(text('PRAGMA foreign_keys = ON'))
            elif 'mysql' in db_url:
                db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))

        # 生成门店数据
        store_data = [
            {"store_id": "190", "store_name": "Central WestGate",
             "store_address": "Central WestGate, 190, 191 Moo 6 Tambon Sao Thong Hin, Amphoe Bang Yai, Nonthaburi 11140, Thailand",
             "third_party_platform": True},
            {"store_id": "191", "store_name": "Central Rama 2",
             "store_address": "Central Rama 2, 128 ถนน พระรามที่ 2 Bang Mot, Chom Thong, Bangkok 10150, Thailand",
             "third_party_platform": False},
            {"store_id": "76", "store_name": "Lasalle 32 Alley",
             "store_address": "Lasalle's 32 Alley Ice cream, 28 Soi Lasalle 32 Bang Na Tai, Bang Na, Bangkok 10260, Thailand",
             "third_party_platform": False},
            {"store_id": "83", "store_name": "Gateway at Bang Sue",
             "store_address": "Gateway at Bangsue, 28 Pracharat Sai 2 Rd, Khwaeng Bang Sue, Khet Bang Sue, Krung Thep Maha Nakhon 10800, Thailand",
             "third_party_platform": True},
            {"store_id": "91", "store_name": "Terminal 21 Pattaya",
             "store_address": "Terminal 21 Pattaya, 456, 777, 777/1 Moo 6 Bang Lamung District, Chon Buri 20150, Thailand",
             "third_party_platform": True},
            {"store_id": "92", "store_name": "The Mail Life Store Ngamwongwan",
             "store_address": "The Mall Life Store Ngamwongwan, 6/188-189 Moo 2,Thanon Ngamwongwan, Bang Khen, Nonthaburi 11000, Thailand",
             "third_party_platform": False},
        ]
        stores = []
        for data in store_data:
            store = Store(**data)
            db.session.add(store)
            stores.append(store)
        db.session.commit()

        # 生成用户数据（admin、管理组、每门店分店长和员工）
        admin_user = User()
        admin_user.username = "admin"
        admin_user.password_hash = generate_password_hash("admin")
        admin_user.role = RoleType.ADMIN
        admin_user.user_status = 1
        admin_user.real_name = fake.name()
        admin_user.email = fake.email()
        admin_user.phone = fake.phone_number()
        admin_user.created_at = datetime.now()
        admin_user.updated_at = datetime.now()
        db.session.add(admin_user)
        db.session.commit()
        # 管理组用户
        for idx, role in enumerate([RoleType.FINANCE, RoleType.HEAD_MANAGER]):
            uname = chr(97 + idx) * 3  # bbb, ccc
            user = User()
            user.username = uname
            user.password_hash = generate_password_hash(uname)
            user.role = role
            user.user_status = 1
            user.real_name = fake.name()
            user.email = fake.email()
            user.phone = fake.phone_number()
            user.created_at = datetime.now()
            user.updated_at = datetime.now()
            db.session.add(user)
        db.session.commit()
        # 门店分店长和员工
        for store in stores:
            # 分店长
            mgr_username = f"mgr_{store.store_id}"
            mgr = User()
            mgr.username = mgr_username
            mgr.password_hash = generate_password_hash(mgr_username)
            mgr.role = RoleType.BRANCH_MANAGER
            mgr.user_status = 1
            mgr.store_id = store.store_id
            mgr.real_name = fake.name()
            mgr.email = fake.email()
            mgr.phone = fake.phone_number()
            mgr.created_at = datetime.now()
            mgr.updated_at = datetime.now()
            db.session.add(mgr)
            # 员工
            emp_username = f"emp_{store.store_id}"
            emp = User()
            emp.username = emp_username
            emp.password_hash = generate_password_hash(emp_username)
            emp.role = RoleType.EMPLOYEE
            emp.user_status = 1
            emp.store_id = store.store_id
            emp.real_name = fake.name()
            emp.email = fake.email()
            emp.phone = fake.phone_number()
            emp.created_at = datetime.now()
            emp.updated_at = datetime.now()
            db.session.add(emp)
        db.session.commit()

        # 生成日报测试数据（3个月，每门店每天一条）
        users = User.query.all()
        store_users = {}
        for store in stores:
            store_users[store.store_id] = [u for u in users if
                                           u.store_id == store.store_id and u.role in [RoleType.BRANCH_MANAGER,
                                                                                       RoleType.EMPLOYEE]]
        today = date.today()
        start_date = (today.replace(day=1) - timedelta(days=3 * 31)).replace(day=1)
        end_date = today
        db.session.query(DailySales).delete()
        db.session.commit()
        for store in stores:
            d = start_date
            while d <= end_date:
                user_list = store_users.get(store.store_id, [])
                if not user_list:
                    d += timedelta(days=1)
                    continue
                user = random.choice(user_list)
                cash_income = round(random.uniform(100, 500), 2)
                pos_income = round(random.uniform(200, 800), 2)
                day_pass_income = round(random.uniform(50, 300), 2)
                voucher_amount = round(random.uniform(0, 50), 2)
                pos_total = round(cash_income + pos_income + day_pass_income + voucher_amount, 2)
                electronic_actual_arrival = round(random.uniform(200, 800), 2)
                bank_deposit = round(random.uniform(100, 500), 2)
                bank_fee = round(random.uniform(0, 10), 2)
                takeaway_amount = round(random.uniform(100, 400), 2)
                actual_sales = round(takeaway_amount + day_pass_income + electronic_actual_arrival + bank_deposit, 2)
                theoretical_total = round(pos_total + takeaway_amount - voucher_amount - bank_deposit, 2)
                # 昨日数据全部设为 APPROVED，其他日期随机
                if d == today - timedelta(days=1):
                    financial_check_status = FinancialCheckStatus.APPROVED
                else:
                    financial_check_status = random.choice([
                        FinancialCheckStatus.PENDING,
                        FinancialCheckStatus.APPROVED
                    ])
                sales = DailySales()
                sales.store_id = store.store_id
                sales.user_id = user.user_id
                sales.report_date = d
                sales.cash_income = cash_income
                sales.pos_income = pos_income
                sales.day_pass_income = day_pass_income
                sales.voucher_amount = voucher_amount
                sales.pos_total = pos_total
                sales.electronic_actual_arrival = electronic_actual_arrival
                sales.bank_deposit = bank_deposit
                sales.bank_fee = bank_fee
                sales.takeaway_amount = takeaway_amount
                sales.actual_sales = actual_sales
                sales.theoretical_total = theoretical_total
                sales.financial_check_status = financial_check_status
                db.session.add(sales)
                d += timedelta(days=1)
        db.session.commit()
        print(f"已生成3个月测试日报数据（昨日全部为 APPROVED）")

        # 生成财务报销申请测试数据（2个月，每门店每天一条）
        db.session.query(ReimbursementRequest).delete()
        db.session.commit()
        admin_user = User.query.filter_by(username='admin').first()
        admin_id = admin_user.user_id if admin_user else None
        start_date = (today.replace(day=1) - timedelta(days=2 * 31)).replace(day=1)
        end_date = today
        for store in stores:
            d = start_date
            while d <= end_date:
                user_list = store_users.get(store.store_id, [])
                if not user_list:
                    d += timedelta(days=1)
                    continue
                user = random.choice(user_list)
                amount = round(random.uniform(100, 2000), 2)
                primary_category = random.choice(list(ReimbursementPrimaryCategory))
                secondary_category = random.choice(list(ReimbursementSecondaryCategory))
                status = random.choice([
                    ReimbursementStatus.APPROVED, ReimbursementStatus.PENDING, ReimbursementStatus.REJECTED])
                approval_comments = fake.sentence() if status == ReimbursementStatus.APPROVED else None
                approved_at = datetime.combine(d,
                                               datetime.min.time()) if status == ReimbursementStatus.APPROVED else None
                reimb = ReimbursementRequest()
                reimb.store_id = store.store_id
                reimb.submitter_id = user.user_id
                reimb.primary_category = primary_category
                reimb.secondary_category = secondary_category
                reimb.amount = amount
                reimb.currency = 'THB'
                reimb.description = f"测试报销申请 {store.store_id} {d}"
                reimb.status = status
                reimb.approver_id = admin_id
                reimb.approval_comments = approval_comments
                reimb.created_at = datetime.combine(d, datetime.min.time())
                reimb.updated_at = datetime.combine(d, datetime.min.time())
                reimb.approved_at = approved_at
                db.session.add(reimb)
                d += timedelta(days=1)
        db.session.commit()
        print(f"已生成2个月财务报销申请测试数据（审批人仅admin，审批意见和审批时间有值）")

    except Exception as e:
        db.session.rollback()
        print(f"❌ 生成测试数据时发生严重错误: {e}")
        raise e


if __name__ == "__main__":
    from app import create_app
    from config import Config

    app = create_app(Config)
    with app.app_context():
        generate_fake_data()
