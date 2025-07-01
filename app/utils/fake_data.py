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
    只保留门店数据和admin用户，其它全部注释掉。
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

            print("开始生成基础数据 (门店和admin用户)...")
            # 1. 门店数据
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

            # 2. 只生成admin用户
            admin_user = User(
                username='admin',
                role=RoleType.ADMIN,
                real_name=fake.name(),
                email=fake.email(),
                phone=fake.phone_number()
            )
            admin_user.set_password('admin')
            db.session.add(admin_user)
            print("✅ admin用户生成完成")

        db.session.commit()

        # --- 其它用户和日报数据全部注释掉 ---
        # 示例：如需生成日报数据，需补充误差字段
        # with db.session.begin_nested():
        #     sales = DailySales(
        #         store_id='190',
        #         user_id=admin_user.user_id,
        #         report_date=datetime.today().date(),
        #         cash_income=1000,
        #         pos_income=500,
        #         day_pass_income=200,
        #         pos_total=1700,
        #         cash_difference=10,  # 新增字段
        #         electronic_difference=-5,  # 新增字段
        #         voucher_amount=50,
        #         takeaway_amount=100,
        #         bank_deposit=1600,
        #         bank_fee=10,
        #         actual_sales=1650,
        #         pos_info_completed=True,
        #         takeaway_info_completed=True,
        #         bank_info_completed=True,
        #         is_submitted=False
        #     )
        #     db.session.add(sales)
        # db.session.commit()
        # print("🎉🎉🎉 仅门店数据和admin用户生成成功！ 🎉🎉🎉")
        # return True

        # --- 示例：生成测试日报数据（含误差字段和附件），如需可取消注释 ---
        # with db.session.begin_nested():
        #     print("开始生成测试日报数据（含 cash_difference、electronic_difference 字段）...")
        #     stores = Store.query.all()
        #     admin = User.query.filter_by(username='admin').first()
        #     for store in stores:
        #         for i in range(3):  # 生成3天的日报
        #             report_date = date.today() - timedelta(days=i)
        #             cash_income = round(random.uniform(500, 2000), 2)
        #             pos_income = round(random.uniform(500, 3000), 2)
        #             day_pass_income = round(random.uniform(100, 800), 2)
        #             pos_total = cash_income + pos_income + day_pass_income
        #             sales = DailySales(
        #                 store_id=store.store_id,
        #                 user_id=admin.user_id,
        #                 report_date=report_date,
        #                 cash_income=cash_income,
        #                 pos_income=pos_income,
        #                 day_pass_income=day_pass_income,
        #                 pos_total=pos_total,
        #                 cash_difference=round(random.uniform(-10, 10), 2),
        #                 electronic_difference=round(random.uniform(-10, 10), 2),
        #                 takeaway_amount=round(random.uniform(100, 800), 2),
        #                 bank_receipt_amount=round(random.uniform(500, 2000), 2),
        #                 bank_fee=round(random.uniform(0, 20), 2),
        #                 bank_deposit=round(random.uniform(500, 2000), 2),
        #                 voucher_amount=round(random.uniform(0, 100), 2),
        #                 actual_sales=round(random.uniform(1000, 5000), 2),
        #                 remark=fake.sentence(),
        #                 pos_info_completed=True,
        #                 takeaway_info_completed=True,
        #                 bank_info_completed=True,
        #                 is_submitted=True,
        #                 financial_check_status=FinancialCheckStatus.PENDING,
        #                 archived=True,
        #                 created_at=datetime.now(),
        #                 updated_at=datetime.now()
        #             )
        #             db.session.add(sales)
        #             db.session.flush()  # 生成ID
        #             # 附件示例
        #             for _ in range(random.randint(1, 2)):
        #                 db.session.add(create_daily_sales_attachment(sales, fake))
        #     print("✅ 测试日报数据生成完成")
        # db.session.commit()
        # print("🎉🎉🎉 测试日报数据（含误差字段和附件）生成成功！ 🎉🎉🎉")
        # return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ 生成测试数据时发生严重错误: {e}")
        raise e


def clean_daily_sales_duplicates():
    """
    清理每个门店每天归档数>1的销售日报，只保留最新一条，其余全部删除。
    """
    from app.models import DailySales
    from sqlalchemy import func
    # 查询所有归档日报分组
    subq = db.session.query(
        DailySales.store_id,
        DailySales.report_date,
        func.count(DailySales.report_id).label('cnt')
    ).filter(DailySales.archived==True).group_by(DailySales.store_id, DailySales.report_date).having(func.count(DailySales.report_id)>1).all()
    total_deleted = 0
    for store_id, report_date, cnt in subq:
        # 找出该组所有归档日报，按创建时间倒序，保留最新一条
        dups = DailySales.query.filter_by(store_id=store_id, report_date=report_date, archived=True).order_by(DailySales.created_at.desc()).all()
        for dup in dups[1:]:
            db.session.delete(dup)
            total_deleted += 1
    db.session.commit()
    print(f"已清理重复归档日报 {total_deleted} 条")
