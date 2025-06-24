# MXStoreBI/app/models/daily_sales.py

# 【核心修正】: 修正了 db 对象的导入路径
from datetime import datetime

from app.extensions import db

from .enums import FinancialCheckStatus


class DailySales(db.Model):
    """
    每日营业额上报记录模型
    """
    __tablename__ = 'daily_sales'

    # --- 模型字段定义 (与上一版一致) ---
    report_id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(32), db.ForeignKey('stores.store_id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    report_date = db.Column(db.Date, nullable=False, index=True)
    total_income = db.Column(db.Float, comment='POS机小票总收入(T)')
    cash_income = db.Column(db.Float, comment='现金收入(C)')
    pos_income = db.Column(db.Float, comment='电子支付收入(P)')
    day_pass_income = db.Column(db.Float, comment='POS系统中记录的外卖收入(D)')
    meituan_takeaway = db.Column(db.Float, comment='第三方外卖收入(美团)')
    eleme_takeaway = db.Column(db.Float, comment='第三方外卖收入(饿了么)')
    bank_receipt_amount = db.Column(db.Float, comment='银行存入的现金金额')

    pos_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第一步(POS)是否完成')
    takeaway_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第二步(外卖)是否完成')
    bank_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第三步(银行)是否完成')
    is_submitted = db.Column(db.Boolean, default=False, nullable=False, comment='是否已最终提交给财务')

    financial_check_status = db.Column(db.Enum(FinancialCheckStatus), default=FinancialCheckStatus.PENDING,
                                       nullable=False, comment='财务核对状态')
    archived = db.Column(db.Boolean, default=False, nullable=False, comment='是否已归档')

    bank_deposit = db.Column(db.Float, comment='财务填写的实际到账金额')
    voucher_amount = db.Column(db.Float, comment='财务填写的代金券金额')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attachments = db.relationship('DailySalesAttachments', backref='daily_sale', lazy='dynamic',
                                  cascade="all, delete-orphan")

    def __repr__(self):
        return f'<DailySales {self.report_id} for Store {self.store_id} on {self.report_date}>'

    def to_dict(self):
        """
        将 DailySales 对象转换为字典格式，方便API返回。
        """
        return {
            "report_id": self.report_id,
            "store_id": self.store_id,
            "user_id": self.user_id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "total_income": self.total_income,
            "cash_income": self.cash_income,
            "pos_income": self.pos_income,
            "day_pass_income": self.day_pass_income,
            "meituan_takeaway": self.meituan_takeaway,
            "eleme_takeaway": self.eleme_takeaway,
            "bank_receipt_amount": self.bank_receipt_amount,
            "pos_info_completed": self.pos_info_completed,
            "takeaway_info_completed": self.takeaway_info_completed,
            "bank_info_completed": self.bank_info_completed,
            "is_submitted": self.is_submitted,
            "financial_check_status": self.financial_check_status.value if self.financial_check_status else None,
            "archived": self.archived,
            "bank_deposit": self.bank_deposit,
            "voucher_amount": self.voucher_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "attachments": [attachment.to_dict() for attachment in self.attachments]
        }