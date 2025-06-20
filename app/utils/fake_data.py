# app/utils/fake_data.py
import random
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.attachment import AttachmentType, DailySalesAttachments
from app.models.daily_sales import DailySales, FinancialCheckStatus, ReportStatus
from app.models.store import Store
from app.models.store_staff import StoreStaff
from app.models.user import RoleType, User
from faker import Faker
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

fake = Faker("zh_CN")

def create_default_admin():
    """生成默认管理员用户，用户名admin，密码admin"""
    admin_username = "admin"
    admin_password = "admin"
    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        hashed_password = generate_password_hash(admin_password)
        admin_user = User(
            username=admin_username,
            password_hash=hashed_password,
            user_status=1,
            role=RoleType.ADMIN,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(admin_user)
        db.session.commit()

def generate_fake_data():
    try:
        # 先清空表，顺序遵循外键依赖，SQL语句必须用text()包裹
        db.session.execute(text('DELETE FROM daily_sales_attachments'))
        db.session.execute(text('DELETE FROM daily_sales'))
        db.session.execute(text('DELETE FROM store_staff'))
        db.session.execute(text('DELETE FROM users'))
        db.session.execute(text('DELETE FROM stores'))
        db.session.commit()

        # 1. 生成门店数据
        store_list = []
        store_ids = ["76", "83", "91", "92", "190", "191"] # 预定义的 store_id 列表

        for i in range(len(store_ids)): # 循环6次
            store_id = store_ids[i]
            store = Store(
                store_id=store_id,
                store_name=f"蜜雪门店_{i+1}",
                store_address=f"https://www.google.com/maps/place/{fake.address().replace(' ', '+')}", # 谷歌地图链接
                third_party_platform=random.choice([True, False])
            )
            store_list.append(store)
        db.session.add_all(store_list)
        db.session.commit()

        # 2. 生成用户，含多角色
        role_choices = [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER,
                        RoleType.BRANCH_MANAGER, RoleType.EMPLOYEE]
        user_list = []
        for i in range(10):
            role = random.choice(role_choices)
            user = User(
                username=f"user_{i}",
                password_hash="pbkdf2:sha256:600000$dummy$hash",  # 假密码哈希，生产环境替换
                user_status=1,
                last_login_time=fake.date_time_between(start_date='-30d', end_date='now'),
                created_at=fake.date_time_between(start_date='-365d', end_date='-30d'),
                updated_at=datetime.now(),
                role=role
            )
            user_list.append(user)
        db.session.add_all(user_list)
        db.session.commit()

        # 3. 生成店铺员工，关联门店和普通用户
        staff_list = []
        normal_users = [u for u in user_list if u.role == RoleType.EMPLOYEE]
        for user in normal_users:
            store = random.choice(store_list)
            staff = StoreStaff(
                store_id=store.store_id,
                user_id=user.user_id,
                bank_account_name=fake.name(),
                bank_account_number=fake.bban(),
                staff_position=fake.job(),
                is_primary_contact=random.choice([True, False]),
                phone=fake.phone_number(),
                line_id=fake.user_name(),
                email=fake.email(),
                start_date=fake.date_between(start_date='-1y', end_date='today'),
                end_date=None,
                created_at=datetime.now()
            )
            staff_list.append(staff)
        db.session.add_all(staff_list)
        db.session.commit()

        # 4. 生成每日营业额日报，近30天，所有门店
        sales_list = []
        today = date.today()
        for store in store_list:
            for i in range(30):
                report_date = today - timedelta(days=i)
                total_income = round(random.uniform(2000, 8000), 2)
                cash_sales = round(total_income * random.uniform(0.2, 0.4), 2)
                electronic_sales = round(total_income * random.uniform(0.3, 0.5), 2)
                system_takeaway_sales = round(total_income * random.uniform(0.05, 0.15), 2)
                takeaway_platform_sales = round(total_income * random.uniform(0.05, 0.15), 2)
                cash_difference = round(random.uniform(-20, 20), 2)
                electronic_difference = round(random.uniform(-10, 10), 2)
                voucher_amount = round(random.uniform(0, 100), 2)
                bank_fee = round(random.uniform(0, 10), 2)
                bank_deposit = total_income - voucher_amount - bank_fee + cash_difference + electronic_difference
                actual_sales = bank_deposit + voucher_amount

                sales = DailySales(
                    store_id=store.store_id,
                    report_date=report_date,
                    total_income=total_income,
                    cash_sales=cash_sales,
                    electronic_sales=electronic_sales,
                    system_takeaway_sales=system_takeaway_sales,
                    takeaway_platform_sales=takeaway_platform_sales,
                    cash_difference=cash_difference,
                    electronic_difference=electronic_difference,
                    voucher_amount=voucher_amount,
                    bank_fee=bank_fee,
                    bank_deposit=bank_deposit,
                    actual_sales=actual_sales,
                    report_status=random.choice(list(ReportStatus)),
                    financial_check_status=random.choice(list(FinancialCheckStatus)),
                    archived=False,
                    created_by=random.choice(user_list).user_id,
                    created_at=datetime.now(),
                    modified_by=random.choice(user_list).user_id,
                    modified_at=datetime.now()
                )
                sales_list.append(sales)
        db.session.add_all(sales_list)
        db.session.commit()

        # 5. 生成日报附件，随机1~3个附件
        attachment_list = []
        for sales_record in sales_list:
            for _ in range(random.randint(1, 3)):
                attachment = DailySalesAttachments(
                    report_id=sales_record.report_id,
                    file_path=fake.file_path(depth=2),
                    attachment_type=random.choice(list(AttachmentType)),
                    created_at=datetime.now()
                )
                attachment_list.append(attachment)
        db.session.add_all(attachment_list)
        db.session.commit()

        print("✅ 测试数据生成成功！")

    except IntegrityError as e:
        db.session.rollback()
        print(f"❌ 生成测试数据失败: {e}")

    except Exception as e:
        db.session.rollback()
        print(f"❌ 生成测试数据异常: {e}")