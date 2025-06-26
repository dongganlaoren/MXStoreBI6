# app/utils/fake_data.py
import random
from datetime import date, datetime, timedelta

from app.extensions import db

# 不再导入 StoreStaff
from app.models import (
    AttachmentType,
    DailySales,
    DailySalesAttachments,
    FinancialCheckStatus,
    RoleType,
    Store,
    User,
)
from faker import Faker
from sqlalchemy import text

# 初始化 Faker
fake = Faker("zh_CN")  # 使用中文数据，可以生成更逼真的中文名等


def create_daily_sales_attachment(sales_record, faker_instance):
    """为日报创建并返回一个附件对象"""
    return DailySalesAttachments(
        report_id=sales_record.report_id,
        file_path=faker_instance.file_path(depth=2),
        attachment_type=random.choice(list(AttachmentType)),
        created_at=datetime.now()
    )


def generate_fake_data():
    """
    生成所有模块的测试数据。
    这个版本已适配合并后的 User 模型。
    """
    try:
        # --- 阶段一：清空并创建基础数据 (门店、管理组用户) ---
        with db.session.begin_nested():
            print("开始清空旧数据...")
            db.session.execute(text('DELETE FROM daily_sales_attachments'))
            db.session.execute(text('DELETE FROM daily_sales'))
            db.session.execute(text('DELETE FROM users'))
            db.session.execute(text('DELETE FROM stores'))
            print("旧数据已清空。")

            print("开始生成基础数据 (门店和管理组)...")
            # 1. 【核心修正】：恢复您原始的、详细的固定门店数据
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
            for data in store_data:
                db.session.add(Store(**data))
            print("✅ 门店数据生成完成")

            # 2. 生成管理组用户 (他们不关联任何 store_id)
            # 【核心修正】：按您的要求统一密码
            management_users_data = [
                {'username': 'admin', 'password': 'admin', 'role': RoleType.ADMIN},
                {'username': 'head_manager', 'password': '123456', 'role': RoleType.HEAD_MANAGER},
                {'username': 'finance', 'password': '123456', 'role': RoleType.FINANCE},
            ]
            for user_data in management_users_data:
                user = User(
                    username=user_data['username'],
                    role=user_data['role'],
                    real_name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number()
                )
                user.set_password(user_data['password'])
                db.session.add(user)
            print("✅ 管理组用户生成完成")

        db.session.commit()

        # --- 阶段二：为每个门店创建门店组用户 ---
        with db.session.begin_nested():
            print("开始为每个门店生成店长和店员...")
            stores = Store.query.all()
            for store in stores:
                # 为每个店创建一个店长
                manager_username = f"manager_{store.store_id.lower()}"
                manager = User(
                    username=manager_username,
                    role=RoleType.BRANCH_MANAGER,
                    store_id=store.store_id, # 关键：关联到当前店铺
                    real_name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    start_date=fake.date_between(start_date='-2y', end_date='-1y'),
                    profile_completed=False
                )
                manager.set_password('123456')
                db.session.add(manager)

                # 为每个店创建2个店员
                for i in range(2):
                    employee_username = f"employee_{store.store_id.lower()}_{i+1}"
                    employee = User(
                        username=employee_username,
                        role=RoleType.EMPLOYEE,
                        store_id=store.store_id, # 关键：关联到当前店铺
                        real_name=fake.name(),
                        email=fake.email(),
                        phone=fake.phone_number(),
                        start_date=fake.date_between(start_date='-1y', end_date='today'),
                        profile_completed=False
                    )
                    employee.set_password('123456')
                    db.session.add(employee)
            print("✅ 门店组用户生成完成")

        db.session.commit()

        # --- 阶段三：创建依赖数据 (日报) ---
        with db.session.begin_nested():
            print("开始生成日报和附件数据...")
            store_users = User.query.filter(User.store_id.isnot(None)).all()
            if not store_users:
                 print("⚠️ 警告: 没有找到任何门店用户，无法生成日报数据。")
                 return True

            attachment_list = []
            for user in store_users:
                # 为每个门店用户生成最近5天的日报
                for i in range(5):
                    report_date = date.today() - timedelta(days=i)
                    sales = DailySales(
                        store_id=user.store_id,
                        user_id=user.user_id,
                        report_date=report_date,
                        total_income=round(random.uniform(2000, 8000), 2),
                        cash_income=round(random.uniform(500, 2000), 2),
                        financial_check_status=random.choice(list(FinancialCheckStatus)),
                    )
                    db.session.add(sales)
                    db.session.flush()
                    attachment_list.extend(
                        [create_daily_sales_attachment(sales, fake) for _ in range(random.randint(0, 2))])

            db.session.add_all(attachment_list)
            print("✅ 日报和附件数据生成完成")

        db.session.commit()
        print("🎉🎉🎉 所有测试数据生成成功！ 🎉🎉🎉")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ 生成测试数据时发生严重错误: {e}")
        raise e
