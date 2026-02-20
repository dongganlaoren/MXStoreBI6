"""
自动生成门店、用户、日报、财务报销申请测试数据，严格符合模型字段定义。
"""
import random
from datetime import datetime

from faker import Faker
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.inventory_stocktake.models import MXMaterialInfo
from app.models import Store, User, DailySales
from app.models.enums import RoleType
from app.models.reimbursement import ReimbursementRequest

fake = Faker("zh_CN")


def _wipe_all_tables() -> None:
    """Dangerous: delete all rows from all tables except alembic_version."""
    bind = db.session.get_bind()
    insp = db.inspect(bind)
    table_names = insp.get_table_names()
    db_url = bind.url.drivername

    if 'sqlite' in db_url:
        db.session.execute(text('PRAGMA foreign_keys = OFF'))
    elif 'mysql' in db_url:
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))

    for table in table_names:
        if not table:
            continue
        if table.lower() in {"alembic_version"}:
            continue
        if table.lower().startswith("sqlite_"):
            continue

        quoted = insp.dialect.identifier_preparer.quote(table)
        db.session.execute(text('DELETE FROM {}'.format(quoted)))

    if 'sqlite' in db_url:
        db.session.execute(text('PRAGMA foreign_keys = ON'))
    elif 'mysql' in db_url:
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))


def generate_fake_data(
        *,
        wipe: bool = True,
        include_stores: bool = True,
        include_users: bool = True,
        include_daily_sales: bool = False,
        include_reimbursement: bool = False,
        include_inventory: bool = True,
) -> None:
    try:
        # 安全措施：禁止在生产环境执行
        # 兼容 Flask 老版本/新版本配置：ENV / FLASK_ENV
        from flask import current_app
        if current_app:
            env = (current_app.config.get('ENV') or current_app.config.get('FLASK_ENV') or '').lower()
            if env == 'production':
                raise RuntimeError('禁止在生产环境运行 fake-data 命令')

        if wipe:
            with db.session.begin_nested():
                _wipe_all_tables()
            db.session.commit()

        stores = []
        if include_stores:
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
            for data in store_data:
                store = Store.query.get(data["store_id"])
                if store is None:
                    store = Store(**data)
                    db.session.add(store)
                else:
                    # keep it idempotent: update basic fields
                    store.store_name = data.get("store_name")
                    store.store_address = data.get("store_address")
                    store.third_party_platform = data.get("third_party_platform")
                stores.append(store)
            db.session.commit()
        else:
            stores = Store.query.all()

        if include_users:
            # 生成用户数据（admin、管理组、每门店分店长和员工）
            admin_user = User.query.filter_by(username="admin").first() or User()
            admin_user.username = "admin"
            admin_user.password_hash = generate_password_hash("admin")
            admin_user.role = RoleType.ADMIN
            admin_user.user_status = 1
            admin_user.real_name = admin_user.real_name or fake.name()
            # 管理组用户不绑定门店
            admin_user.store_id = None
            # 要求：固定 admin 邮箱
            admin_user.email = "32191681@qq.com"
            admin_user.phone = admin_user.phone or fake.phone_number()
            admin_user.created_at = admin_user.created_at or datetime.now()
            admin_user.updated_at = datetime.now()
            admin_user.employee_number = admin_user.employee_number or (random.randint(1, 9) * 11111)
            db.session.add(admin_user)
            db.session.commit()

            # 要求：新增管理组用户 aaa 并指定邮箱
            aaa = User.query.filter_by(username="aaa").first() or User()
            aaa.username = "aaa"
            aaa.password_hash = generate_password_hash("aaa")
            aaa.role = RoleType.FINANCE
            aaa.user_status = 1
            aaa.real_name = aaa.real_name or fake.name()
            # 管理组用户不绑定门店
            aaa.store_id = None
            aaa.email = "renweimin@gmail.com"
            aaa.phone = aaa.phone or fake.phone_number()
            aaa.created_at = aaa.created_at or datetime.now()
            aaa.updated_at = datetime.now()
            aaa.employee_number = aaa.employee_number or (random.randint(1, 9) * 11111)
            db.session.add(aaa)

            # 其他管理组用户（保留原逻辑）
            for idx, role in enumerate([RoleType.HEAD_MANAGER]):
                uname = "ccc"  # 仅保留一个示例管理用户
                user = User.query.filter_by(username=uname).first() or User()
                user.username = uname
                user.password_hash = generate_password_hash(uname)
                user.role = role
                user.user_status = 1
                user.real_name = user.real_name or fake.name()
                user.store_id = None
                user.email = user.email or fake.email()
                user.phone = user.phone or fake.phone_number()
                user.created_at = user.created_at or datetime.now()
                user.updated_at = datetime.now()
                user.employee_number = user.employee_number or (random.randint(1, 9) * 11111)
                db.session.add(user)
            db.session.commit()

            # 门店分店长和员工
            for store in stores:
                # 分店长
                mgr_username = "mgr_{}".format(store.store_id)
                mgr = User.query.filter_by(username=mgr_username).first() or User()
                mgr.username = mgr_username
                mgr.password_hash = generate_password_hash(mgr_username)
                mgr.role = RoleType.BRANCH_MANAGER
                mgr.user_status = 1
                mgr.store_id = store.store_id
                mgr.real_name = mgr.real_name or fake.name()
                mgr.email = mgr.email or fake.email()
                mgr.phone = mgr.phone or fake.phone_number()
                mgr.created_at = mgr.created_at or datetime.now()
                mgr.updated_at = datetime.now()
                # employee_number: 门店ID + 3位序号 (例如 91123)
                try:
                    mgr.employee_number = mgr.employee_number or int("{}{:03d}".format(int(store.store_id), random.randint(1, 999)))
                except Exception:
                    mgr.employee_number = mgr.employee_number or (random.randint(1, 9) * 11111)
                db.session.add(mgr)

                # 员工
                emp_username = "emp_{}".format(store.store_id)
                emp = User.query.filter_by(username=emp_username).first() or User()
                emp.username = emp_username
                emp.password_hash = generate_password_hash(emp_username)
                emp.role = RoleType.EMPLOYEE
                emp.user_status = 1
                emp.store_id = store.store_id
                emp.real_name = emp.real_name or fake.name()
                emp.email = emp.email or fake.email()
                emp.phone = emp.phone or fake.phone_number()
                emp.created_at = emp.created_at or datetime.now()
                emp.updated_at = datetime.now()
                try:
                    emp.employee_number = emp.employee_number or int("{}{:03d}".format(int(store.store_id), random.randint(1, 999)))
                except Exception:
                    emp.employee_number = emp.employee_number or (random.randint(1, 9) * 11111)
                db.session.add(emp)
            db.session.commit()

        if include_inventory:
            # 生成物料信息
            materials = [
                {"material_code": "M001", "cn_name": "柠檬", "spec_model": "15kg/件", "category": "食材类",
                 "per_group_qty": 1},
                {"material_code": "M002", "cn_name": "珍珠", "spec_model": "1kg/包", "category": "食材类",
                 "per_group_qty": 20},
                {"material_code": "M003", "cn_name": "茶叶", "spec_model": "500g/袋", "category": "食材类",
                 "per_group_qty": 10},
                {"material_code": "P001", "cn_name": "杯子", "spec_model": "500ml", "category": "包材类",
                 "per_group_qty": 50},
                {"material_code": "P002", "cn_name": "吸管", "spec_model": "粗管", "category": "包材类",
                 "per_group_qty": 100},
            ]

            for m_data in materials:
                m = MXMaterialInfo.query.filter_by(material_code=m_data["material_code"]).first() or MXMaterialInfo(**m_data)
                m.material_code = m_data["material_code"]
                m.cn_name = m_data["cn_name"]
                m.spec_model = m_data["spec_model"]
                m.category = m_data["category"]
                m.per_group_qty = m_data["per_group_qty"]

                # 随机生成价格
                m.price_per_case = m.price_per_case or round(random.uniform(500, 2000), 2)
                m.price_per_group = m.price_per_group or round(float(m.price_per_case) / m.per_group_qty, 2)
                m.safety_stock = m.safety_stock or random.randint(10, 50)
                m.remark = m.remark or "测试物料"
                db.session.add(m)
            db.session.commit()

            print("✅ 基础物料信息生成完成")

        # 下面两块默认不生成，只有显式开启才做
        if include_daily_sales:
            # TODO: 按需要生成日报测试数据
            pass
        else:
            # 仅清空后跳过插入（保留原行为）
            try:
                # 只在表存在且会话可用时清理，避免某些环境外键约束/权限问题
                db.session.query(DailySales).delete(synchronize_session=False)
                db.session.commit()
            except Exception:
                db.session.rollback()

        if include_reimbursement:
            # TODO: 按需要生成报销测试数据
            pass
        else:
            try:
                db.session.query(ReimbursementRequest).delete(synchronize_session=False)
                db.session.commit()
            except Exception:
                db.session.rollback()

    except Exception as e:
        db.session.rollback()
        print("❌ 生成测试数据时发生严重错误: {}".format(e))
        raise


if __name__ == "__main__":
    from app import create_app
    from config import Config

    app = create_app(Config)
    with app.app_context():
        generate_fake_data()
