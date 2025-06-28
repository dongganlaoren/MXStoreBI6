# MXStoreBI/app/models/daily_sales.py

# 【核心修正】: 修正了 db 对象的导入路径
from datetime import datetime
from flask import current_app

from app.extensions import db

from .enums import FinancialCheckStatus


class DailySales(db.Model):
    """
    每日营业额上报记录模型
    适配泰国本地业务，外卖收入统一为第三方平台，无美团/饿了么字段
    """
    __tablename__ = 'daily_sales'

    # --- 模型字段定义 (与上一版一致) ---
    report_id = db.Column(db.Integer, primary_key=True, comment='日报主键')
    store_id = db.Column(db.String(32), db.ForeignKey('stores.store_id'), nullable=False, index=True, comment='门店ID')
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True, comment='上报人ID')
    report_date = db.Column(db.Date, nullable=False, index=True, comment='营业日期')

    # POS相关收入
    cash_income = db.Column(db.Float, comment='POS现金收入(C)')
    pos_income = db.Column(db.Float, comment='POS电子支付收入(P)')
    day_pass_income = db.Column(db.Float, comment='POS系统中记录的外卖收入(D)')
    pos_total = db.Column(db.Float, comment='POS机小票总收入(T)，=现金+电子支付+POS外卖')
    # --- 新增：误差字段 ---
    cash_difference = db.Column(db.Float, comment='POS现金收入误差(A)')
    electronic_difference = db.Column(db.Float, comment='POS电子支付误差(B)')
    # 统一外卖平台收入（泰国本地如Foodpanda、Grab等）
    takeaway_amount = db.Column(db.Float, comment='第三方外卖平台收入')

    # 银行相关
    bank_receipt_amount = db.Column(db.Float, comment='银行存入的现金金额')
    bank_fee = db.Column(db.Float, comment='银行存款手续费')
    bank_deposit = db.Column(db.Float, comment='财务填写的实际到账金额')

    # 其它
    voucher_amount = db.Column(db.Float, comment='财务填写的代金券金额')
    actual_sales = db.Column(db.Float, comment='店铺实际营业额（财务核对后）')
    remark = db.Column(db.String(255), comment='备注')

    # 步骤与状态
    pos_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第一步(POS)是否完成')
    takeaway_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第二步(外卖)是否完成')
    bank_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第三步(银行)是否完成')
    is_submitted = db.Column(db.Boolean, default=False, nullable=False, comment='是否已最终提交给财务')
    financial_check_status = db.Column(db.Enum(FinancialCheckStatus), default=FinancialCheckStatus.PENDING,
                                       nullable=False, comment='财务核对状态')
    archived = db.Column(db.Boolean, default=False, nullable=False, comment='是否已归档')

    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 附件关联
    attachments = db.relationship('DailySalesAttachments', backref='daily_sale', lazy='dynamic',
                                  cascade="all, delete-orphan")

    def __repr__(self):
        current_app.logger.info(f"[营业日报] 查询日报: id={self.report_id}, 门店={self.store_id}, 日期={self.report_date}")
        return f'<DailySales {self.report_id} for Store {self.store_id} on {self.report_date}>'

    def to_dict(self):
        """
        将 DailySales 对象转换为字典格式，方便API返回。
        """
        current_app.logger.debug(f"[营业日报] to_dict: {self.report_id}")
        return {
            "report_id": self.report_id,
            "store_id": self.store_id,
            "user_id": self.user_id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "cash_income": self.cash_income,
            "pos_income": self.pos_income,
            "day_pass_income": self.day_pass_income,
            "pos_total": self.pos_total,
            # --- 新增 ---
            "cash_difference": self.cash_difference,
            "electronic_difference": self.electronic_difference,
            # --- end ---
            "takeaway_amount": self.takeaway_amount,
            "bank_receipt_amount": self.bank_receipt_amount,
            "bank_fee": self.bank_fee,
            "bank_deposit": self.bank_deposit,
            "voucher_amount": self.voucher_amount,
            "actual_sales": self.actual_sales,
            "remark": self.remark,
            "pos_info_completed": self.pos_info_completed,
            "takeaway_info_completed": self.takeaway_info_completed,
            "bank_info_completed": self.bank_info_completed,
            "is_submitted": self.is_submitted,
            "financial_check_status": self.financial_check_status.value if self.financial_check_status else None,
            "archived": self.archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "attachments": [attachment.to_dict() for attachment in self.attachments]
        }