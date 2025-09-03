"""
自动生成门店、用户、日报、财务报销申请测试数据，严格符合模型字段定义。
"""
from datetime import datetime, date

from faker import Faker
from sqlalchemy import text
from werkzeug.security import generate_password_hash
import random

from app.extensions import db
from app.models import Store, User, DailySales
from app.models.enums import RoleType
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
            # 仅清空非 alembic_version 表
            for table in table_names:
                if table and table.lower() == "alembic_version":
                    # 明确跳过版本表，避免迁移状态被破坏
                    print("跳过 alembic_version 表，不进行清空/修改")
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
        # 要求：固定 admin 邮箱
        admin_user.email = "32191681@qq.com"
        admin_user.phone = fake.phone_number()
        admin_user.created_at = datetime.now()
        admin_user.updated_at = datetime.now()
        admin_user.employee_number = random.randint(1, 9) * 11111
        db.session.add(admin_user)
        db.session.commit()

        # 要求：新增管理组用户 aaa 并指定邮箱
        aaa = User()
        aaa.username = "aaa"
        aaa.password_hash = generate_password_hash("aaa")
        aaa.role = RoleType.FINANCE
        aaa.user_status = 1
        aaa.real_name = fake.name()
        aaa.email = "renweimin@gmail.com"
        aaa.phone = fake.phone_number()
        aaa.created_at = datetime.now()
        aaa.updated_at = datetime.now()
        aaa.employee_number = random.randint(1, 9) * 11111
        db.session.add(aaa)

        # 其他管理组用户（保留原逻辑）
        for idx, role in enumerate([RoleType.HEAD_MANAGER]):
            uname = "ccc"  # 仅保留��个示例管理用户
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
            user.employee_number = random.randint(1, 9) * 11111
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
            mgr.employee_number = int(store.store_id) * 1000 + random.randint(100, 999)
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
            emp.employee_number = int(store.store_id) * 1000 + random.randint(100, 999)
            db.session.add(emp)
        db.session.commit()

        # 预备 store -> users 映射供后续报销数据使用
        users = User.query.all()
        store_users = {}
        for store in stores:
            store_users[store.store_id] = [u for u in users if
                                           u.store_id == store.store_id and u.role in [RoleType.BRANCH_MANAGER,
                                                                                       RoleType.EMPLOYEE]]
        today = date.today()

        # 暂停生成日报测试数据：仅清空后跳过插入
        db.session.query(DailySales).delete()
        db.session.commit()
        print("已跳过日报测试数据生成（按要求暂时取消）")

        # 暂停生成财务报销申请测试数据：仅清空后跳过插入
        db.session.query(ReimbursementRequest).delete()
        db.session.commit()
        print("已跳过财务报销申请测试数据生成（按要求暂时取消）")

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
