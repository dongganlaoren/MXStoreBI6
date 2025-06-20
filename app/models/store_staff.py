# app/models/store_staff.py
from datetime import datetime

from app.extensions import db


class StoreStaff(db.Model):
    """店铺员工模型"""
    __tablename__ = "store_staff"

    staff_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="员工主键")
    store_id = db.Column(db.String(32), db.ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False, comment="所属店铺 ID")
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, comment="用户 ID")
    bank_account_name = db.Column(db.String(64), nullable=False, comment="开户行名称")
    bank_account_number = db.Column(db.String(64), nullable=False, comment="银行卡号")
    staff_position = db.Column(db.String(50), nullable=False, comment="职位")
    is_primary_contact = db.Column(db.Boolean, default=False, comment="是否主联系人")
    phone = db.Column(db.String(32), comment="电话")
    line_id = db.Column(db.String(64), comment="Line账号")
    email = db.Column(db.String(100), comment="邮箱地址")
    start_date = db.Column(db.Date, nullable=False, comment="入职日期")
    end_date = db.Column(db.Date, default=None, comment="离职日期")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<StoreStaff {self.staff_position}>"

    def to_dict(self):
        return {
            "staff_id": self.staff_id,
            "store_id": self.store_id,
            "user_id": self.user_id,
            "bank_account_name": self.bank_account_name,
            "bank_account_number": self.bank_account_number,
            "staff_position": self.staff_position,
            "is_primary_contact": self.is_primary_contact,
            "phone": self.phone,
            "line_id": self.line_id,
            "email": self.email,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_at": self.created_at,
        }
