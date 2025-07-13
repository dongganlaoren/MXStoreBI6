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
    """
    为日报创建并返回一个附件对象（仅用于测试数据生成）。
    """
    return DailySalesAttachments(
        report_id=sales_record.report_id,
        file_path=faker_instance.file_path(depth=2),
        attachment_type=random.choice(list(AttachmentType)),
        created_at=datetime.now()
    )


def generate_fake_data():
    """
    生成基础测试数据：门店信息和admin用户。
    如需生成日报等业务数据，请参考注释示例，自行扩展。
    """

    try:
        # --- 阶段一：清空并创建基础数据 (门店、用户) ---
        with db.session.begin_nested():
            print("开始清空旧数据...")
            db.session.execute(text('DELETE FROM daily_sales_attachments'))
            db.session.execute(text('DELETE FROM daily_sales'))
            db.session.execute(text('DELETE FROM users'))
            db.session.execute(text('DELETE FROM stores'))
            print("旧数据已清空。")

            print("开始生成基础数据 (门店和用户)...")
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
            stores = []
            for data in store_data:
                store = Store(**data)
                db.session.add(store)
                stores.append(store)
            print("✅ 门店数据生成完成")

            # 2. 只保留admin用户，密码同用户名，employee_number 为空
            users = []
            admin_user = User(
                username="admin",
                role=RoleType.ADMIN,
                real_name=fake.name(),
                email=fake.email(),
                phone=fake.phone_number(),
                store_id=None,
                employee_number=None
            )
            admin_user.set_password("admin")
            db.session.add(admin_user)
            users.append(admin_user)

            # 3. 生成所有角色的简单用户，用户名如 aaa、bbb、ccc、ddd、eee，密码同用户名
            simple_users = []
            role_list = [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]
            for idx, role in enumerate(role_list):
                uname = chr(97+idx)*3  # aaa, bbb, ccc
                user = User(
                    username=uname,
                    role=role,
                    real_name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    store_id=None,
                    employee_number=None
                )
                user.set_password(uname)
                db.session.add(user)
                simple_users.append(user)
            # 为每个门店生成至少一个分店长和一个员工
            store_employee_counter = {s.store_id: 0 for s in stores}
            for store in stores:
                # 分店长
                store_employee_counter[store.store_id] += 1
                emp_seq_mgr = str(store_employee_counter[store.store_id]).zfill(3)
                employee_number_mgr = int(f"{store.store_id}{emp_seq_mgr}")
                mgr_username = f"mgr_{store.store_id}"
                mgr = User(
                    username=mgr_username,
                    role=RoleType.BRANCH_MANAGER,
                    real_name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    store_id=store.store_id,
                    employee_number=employee_number_mgr
                )
                mgr.set_password(mgr_username)
                db.session.add(mgr)
                simple_users.append(mgr)
                # 员工
                store_employee_counter[store.store_id] += 1
                emp_seq_emp = str(store_employee_counter[store.store_id]).zfill(3)
                employee_number_emp = int(f"{store.store_id}{emp_seq_emp}")
                emp_username = f"emp_{store.store_id}"
                emp = User(
                    username=emp_username,
                    role=RoleType.EMPLOYEE,
                    real_name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    store_id=store.store_id,
                    employee_number=employee_number_emp
                )
                emp.set_password(emp_username)
                db.session.add(emp)
                simple_users.append(emp)
            users.extend(simple_users)
            print("✅ 简单用户生成完成（含所有角色，且每个门店至少有分店长和员工）")

        db.session.commit()

        # --- 阶段二：生成100条合理的日报数据 ---
        print("开始生成日报数据...")
        today = date.today()
        all_users = users  # admin + simple_users
        num_reports = 100
        for i in range(num_reports):
            store = random.choice(stores)
            user = random.choice(all_users)
            report_date = today - timedelta(days=random.randint(0, 29))
            # 状态分布更均匀
            status = random.choice([FinancialCheckStatus.PENDING, FinancialCheckStatus.APPROVED])
            sales = DailySales(
                user_id=user.user_id,
                store_id=store.store_id,
                report_date=report_date,
                cash_income=round(random.uniform(100, 500), 2),
                pos_income=round(random.uniform(200, 800), 2),
                day_pass_income=round(random.uniform(50, 300), 2),
                voucher_amount=round(random.uniform(0, 50), 2),
                pos_total=0,  # 稍后自动算
                electronic_actual_arrival=round(random.uniform(200, 800), 2),
                bank_deposit=round(random.uniform(100, 500), 2),
                bank_fee=round(random.uniform(0, 10), 2),
                takeaway_amount=round(random.uniform(100, 400), 2),
                actual_sales=0,  # 稍后自动算
                total_error=0,   # 稍后自动算
                cash_difference=round(random.uniform(-10, 10), 2),
                electronic_difference=round(random.uniform(-10, 10), 2),
                remark=fake.sentence(),
                pos_info_completed=True,
                takeaway_info_completed=True,
                actual_arrival_info_completed=True,
                is_submitted=True,
                financial_check_status=status,
                created_at=datetime.now() - timedelta(days=random.randint(0, 29)),
                updated_at=datetime.now() - timedelta(days=random.randint(0, 29))
            )
            # 自动计算
            sales.pos_total = sales.cash_income + sales.pos_income + sales.day_pass_income + sales.voucher_amount
            sales.actual_sales = sales.takeaway_amount + sales.day_pass_income + sales.electronic_actual_arrival + sales.bank_deposit
            sales.total_error = sales.electronic_actual_arrival + sales.bank_deposit + sales.bank_fee - sales.pos_income - sales.cash_income
            db.session.add(sales)
            db.session.flush()  # 确保sales.report_id有值
            # 附件
            for _ in range(random.randint(1, 2)):
                att = create_daily_sales_attachment(sales, fake)
                db.session.add(att)
        db.session.commit()
        print("✅ 日报数据生成完成")

    except Exception as e:
        db.session.rollback()
        print(f"❌ 生成测试数据时发生严重错误: {e}")
        raise e


