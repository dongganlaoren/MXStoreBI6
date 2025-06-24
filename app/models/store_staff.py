# app/models/store_staff.py

from datetime import datetime

from app.extensions import db


class StoreStaff(db.Model):
    """
    员工详细信息模型
    """
    __tablename__ = "store_staff"

    # 【核心修正 1】: 恢复独立的、自增的 staff_id 作为主键
    staff_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 【核心修正 2】: user_id 仍然是外键，但我们给它加上了 unique=True 的约束
    # unique=True 能从数据库层面保证，一个 user_id 最多只能在 staff 表中出现一次，从而严格实现了“一对一”关系
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False,
                        comment="关联的用户ID (唯一)")

    # 关联的店铺ID
    store_id = db.Column(db.String(32), db.ForeignKey("stores.store_id"), nullable=False, comment="关联店铺ID")

    # 员工的个人联系方式和银行信息
    bank_account_name = db.Column(db.String(100), comment="银行账户名")
    bank_account_number = db.Column(db.String(100), comment="银行账号")

    # 【确认修改】: staff_position 字段已被移除

    is_primary_contact = db.Column(db.Boolean, default=False, comment="是否为主要联系人")
    phone = db.Column(db.String(50), comment="联系电话")
    line_id = db.Column(db.String(100), comment="LINE ID")
    email = db.Column(db.String(100), comment="电子邮箱")

    # 在职日期
    start_date = db.Column(db.Date, comment="入职日期")
    end_date = db.Column(db.Date, nullable=True, comment="离职日期")

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StoreStaff for User ID: {self.user_id}>"

    def to_dict(self):
        """将对象转换为字典，方便使用。"""
        return {
            "staff_id": self.staff_id,
            "user_id": self.user_id,
            "store_id": self.store_id,
            "bank_account_name": self.bank_account_name,
            "bank_account_number": self.bank_account_number,
            "is_primary_contact": self.is_primary_contact,
            "phone": self.phone,
            "line_id": self.line_id,
            "email": self.email,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }