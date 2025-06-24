# app/utils/fake_data.py
import random
from datetime import date, datetime, timedelta

from app.extensions import db

# 确保从 __init__ 中导入所有需要的模型和枚举
from app.models import (
    AttachmentType,
    DailySales,
    DailySalesAttachments,
    FinancialCheckStatus,
    RoleType,
    Store,
    StoreStaff,
    User,
)
from faker import Faker
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

fake = Faker("en_US")  # 使用英文地址


def create_daily_sales_attachment(sales_record, fake):
    """创建并返回 DailySalesAttachments 对象"""
    attachment = DailySalesAttachments(
        report_id=sales_record.report_id,
        file_path=fake.file_path(depth=2),
        attachment_type=random.choice(list(AttachmentType)),
        created_at=datetime.now()
    )
    return attachment


def generate_fake_data():
    """
    生成测试数据。
    返回:
        bool: 如果所有操作都成功，则返回 True, 否则返回 False.
    """
    try:
        # --- 阶段一：清空并创建基础数据 (门店、用户) ---
        with db.session.begin_nested():  # 使用嵌套事务，更安全
            print("开始清空旧数据...")
            db.session.execute(text('DELETE FROM daily_sales_attachments'))
            db.session.execute(text('DELETE FROM daily_sales'))
            db.session.execute(text('DELETE FROM store_staff'))
            db.session.execute(text('DELETE FROM users'))
            db.session.execute(text('DELETE FROM stores'))
            print("旧数据已清空，开始生成基础数据...")

            # 1. 生成固定门店数据
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

            # 2. 生成用户
            admin_user = User(username="admin", role=RoleType.ADMIN, user_status=1)
            admin_user.set_password("admin")
            db.session.add(admin_user)

            employee_user = User(username="employee_0", role=RoleType.EMPLOYEE, user_status=1)
            employee_user.set_password("123456")
            db.session.add(employee_user)
            print("✅ 用户数据生成完成")

        db.session.commit()  # 提交第一阶段

        # --- 阶段二：创建依赖数据 ---
        with db.session.begin_nested():
            print("开始生成依赖数据...")
            store_list = Store.query.all()
            user_list = User.query.all()
            attachment_list = []

            if store_list and user_list:
                for store in store_list:
                    for i in range(10):
                        report_date = date.today() - timedelta(days=i)
                        sales = DailySales(
                            store_id=store.store_id,
                            user_id=random.choice(user_list).user_id,
                            report_date=report_date,
                            total_income=round(random.uniform(2000, 8000), 2),
                            cash_income=round(random.uniform(500, 2000), 2),
                            pos_income=round(random.uniform(1000, 4000), 2),
                            day_pass_income=round(random.uniform(500, 2000), 2),
                            bank_receipt_amount=round(random.uniform(500, 2000), 2),
                            voucher_amount=round(random.uniform(0, 100), 2),
                            bank_deposit=round(random.uniform(2000, 8000), 2),
                            pos_info_completed=True,
                            takeaway_info_completed=random.choice([True, False]),
                            bank_info_completed=random.choice([True, False]),
                            is_submitted=random.choice([True, False]),
                            financial_check_status=random.choice(list(FinancialCheckStatus)),
                            archived=False,
                        )
                        db.session.add(sales)
                        db.session.flush()
                        attachment_list.extend(
                            [create_daily_sales_attachment(sales, fake) for _ in range(random.randint(0, 2))])

            db.session.add_all(attachment_list)
            print("✅ 日报和附件数据准备完成")

        db.session.commit()  # 提交第二阶段

        # 【核心修改 1】: 在所有操作成功完成后，明确返回 True
        return True

    except Exception as e:
        # 【核心修改 2】: 在任何异常发生时，打印错误并明确返回 False
        db.session.rollback()
        print(f"❌ 生成测试数据时发生异常: {e}")
        return False

    # 【核心修改 3】: 移除了 finally 块，确保不再打印不准确的成功信息