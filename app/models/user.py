# app/models/user.py

from datetime import datetime

from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

# 从我们统一的 enums.py 文件中导入 RoleType
from .enums import RoleType


class User(UserMixin, db.Model):
    """
    系统用户模型（已合并员工档案信息）
    """
    __tablename__ = "users"

    # --- 原有 User 字段 ---
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="用户主键，自增 ID")
    username = db.Column(db.String(64), unique=True, nullable=False, comment="登录用户名")
    password_hash = db.Column(db.String(255), nullable=False, comment="登录密码哈希")
    user_status = db.Column(db.Integer, nullable=False, default=1, comment="用户状态（1=活跃，0=禁用）")
    last_login_time = db.Column(db.DateTime, default=datetime.now, comment="最近一次登录时间")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    role = db.Column(db.Enum(RoleType), default=RoleType.EMPLOYEE, comment="用户角色")

    # --- 新增：从 StoreStaff 合并过来的字段 ---

    # 【核心修正】: 关联的店铺ID，nullable=True 意味着该字段可以为空。
    # 这完美地满足了“管理组”用户（如ADMIN, FINANCE）不隶属于任何单个店铺的需求。
    # 只有“门店组”用户（如BRANCH_MANAGER, EMPLOYEE）才需要赋予这个字段一个具体的店铺ID。
    store_id = db.Column(db.String(32), db.ForeignKey("stores.store_id"), nullable=True,
                         comment="关联店铺ID (门店组用户专属)")

    # 员工的个人详细信息，这些字段都允许为空（nullable=True），方便分阶段录入
    real_name = db.Column(db.String(100), nullable=True, comment="真实姓名")
    id_card_number = db.Column(db.String(100), nullable=True, comment="身份证号")
    bank_name = db.Column(db.String(100), nullable=True, comment="银行名称")
    bank_account_number = db.Column(db.String(100), nullable=True, comment="银行账号")
    is_primary_contact = db.Column(db.Boolean, default=False, comment="是否为店铺主要联系人")
    phone = db.Column(db.String(50), nullable=True, comment="联系电话")
    line_id = db.Column(db.String(100), nullable=True, comment="LINE ID")
    email = db.Column(db.String(100), nullable=True, comment="电子邮箱")
    start_date = db.Column(db.Date, nullable=True, comment="入职日期")
    end_date = db.Column(db.Date, nullable=True, comment="离职日期")
    profile_completed = db.Column(db.Boolean, default=False, comment="员工档案是否已完善（仅能一次性填写）")

    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        """将对象转换为字典，现在包含所有合并后的字段。"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_status": self.user_status,
            "role": self.role.value if self.role else None,
            "store_id": self.store_id,
            "real_name": self.real_name,
            "id_card_number": self.id_card_number,
            "bank_name": self.bank_name,
            "bank_account_number": self.bank_account_number,
            "is_primary_contact": self.is_primary_contact,
            "phone": self.phone,
            "line_id": self.line_id,
            "email": self.email,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_id)
