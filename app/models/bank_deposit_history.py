# app/models/bank_deposit_history.py
from datetime import datetime
from app.extensions import db
from .enums import BankDepositHistoryAction

class BankDepositHistory(db.Model):
    """
    实际到账金额修改历史记录表
    记录每次 bank_deposit 字段的填写与修改，便于追溯
    """
    __tablename__ = 'bank_deposit_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_id = db.Column(db.Integer, db.ForeignKey('daily_sales.report_id', ondelete='CASCADE'), nullable=False, index=True, comment='日报ID')
    old_value = db.Column(db.Float, comment='原实际到账金额')
    new_value = db.Column(db.Float, nullable=False, comment='新实际到账金额')
    action = db.Column(db.Enum(BankDepositHistoryAction), nullable=False, comment='操作类型（CREATE/MODIFY）')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='操作人ID')
    operator_role = db.Column(db.String(32), comment='操作人角色')
    remark = db.Column(db.String(255), comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='操作时间')

    def __repr__(self):
        return f'<BankDepositHistory {self.report_id} {self.action} {self.created_at}>'
