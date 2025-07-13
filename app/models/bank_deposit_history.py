# app/models/bank_deposit_history.py
from datetime import datetime
from app.extensions import db

class BankDepositHistory(db.Model):
    """
    关键字段修改历史记录表
    记录每次 cash_income、pos_income、takeaway_amount、electronic_actual_arrival、bank_deposit、bank_fee 字段的填写与修改，便于追溯
    """
    __tablename__ = 'bank_deposit_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_id = db.Column(db.Integer, db.ForeignKey('daily_sales.report_id', ondelete='CASCADE'), nullable=False, index=True, comment='日报ID')
    field_name = db.Column(db.String(64), nullable=False, comment='字段名')
    old_value = db.Column(db.Float, comment='原值')
    new_value = db.Column(db.Float, nullable=False, comment='新值')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment='操作人ID')
    operator_role = db.Column(db.String(32), comment='操作人角色')
    remark = db.Column(db.String(255), nullable=False, comment='变更理由')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='操作时间')

    def __repr__(self):
        return f'<BankDepositHistory {self.report_id} {self.field_name} {self.old_value}->{self.new_value} {self.created_at}>'
