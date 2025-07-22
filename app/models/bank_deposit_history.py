# app/models/bank_deposit_history.py
from datetime import datetime

from app.extensions import db


class BankDepositHistory(db.Model):
    """
    银行存款历史记录模型 - 用于记录营业信息的修改历史
    """

    __tablename__ = "bank_deposit_history"

    history_id = db.Column(
        db.Integer, primary_key=True, comment="历史记录主键"
    )
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("daily_sales.report_id"),
        nullable=False,
        comment="关联的日报ID",
    )
    field_name = db.Column(
        db.String(50), nullable=False, comment="被修改的字段名"
    )
    old_value = db.Column(db.Float, comment="修改前的值")
    new_value = db.Column(db.Float, comment="修改后的值")
    operator_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False,
        comment="操作员ID",
    )
    operator_role = db.Column(db.String(50), comment="操作员角色")
    remark = db.Column(db.String(500), comment="修改理由/备注")
    created_at = db.Column(
        db.DateTime, default=datetime.now, comment="创建时间"
    )

    def __repr__(self):
        return f"<BankDepositHistory {self.history_id}>"
