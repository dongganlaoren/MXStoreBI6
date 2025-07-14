# MXStoreBI/app/models/daily_sales.py

from datetime import datetime
from flask import current_app

from app.extensions import db
from .enums import FinancialCheckStatus


class DailySales(db.Model):
    # 门店对象（Store）
    store = db.relationship('Store', backref='daily_sales', lazy='joined')
    # 上报人对象（User）
    user = db.relationship('User', backref='daily_sales', lazy='joined')
    # 理论营收总金额
    theoretical_total = db.Column(db.Float, comment='理论营收(T2)=店铺理论营业额(T0)+第三方外卖平台收入(T1)-POS机小票里显示的代金券总金额-银行存款金额')
    """
    每日营业额上报记录模型
    字段及计算公式详见《字段说明.md》
    """
    __tablename__ = 'daily_sales'

    # --- 模型字段定义 (与上一版一致) ---
    report_id = db.Column(db.Integer, primary_key=True, comment='日报主键')
    store_id = db.Column(db.String(32), db.ForeignKey('stores.store_id'), nullable=False, index=True, comment='门店ID')
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True, comment='上报人ID')
    report_date = db.Column(db.Date, nullable=False, index=True, comment='营业日期')

    # 收银机小票信息录入
    cash_income = db.Column(db.Float, comment='现金收入 (C)')
    pos_income = db.Column(db.Float, comment='电子支付收入 (P)')
    day_pass_income = db.Column(db.Float, comment='外卖收入 (D)')
    voucher_amount = db.Column(db.Float, comment='代金券使用金额 (R)')

    # 店铺理论营业额
    pos_total = db.Column(db.Float, comment='店铺理论营业额 (T0) = 现金收入 + 电子支付收入 + 外卖收入 + 代金券使用金额')

    # 实际入账
    electronic_actual_arrival = db.Column(db.Float, comment='电子支付实际入账金额 (EA)')
    bank_deposit = db.Column(db.Float, comment='银行存款金额 (BC)')
    bank_fee = db.Column(db.Float, comment='银行存款手续费 (BF)')

    # 第三方外卖平台
    takeaway_amount = db.Column(db.Float, default=0.0, nullable=False, comment='第三方外卖平台收入 (T1)')

    # 实际总营业额
    actual_sales = db.Column(db.Float, comment='实际总营业额(S)=第三方外卖平台收入(T1)+外卖收入+电子支付实际入账金额+银行存款金额')

    # 误差
    total_error = db.Column(db.Float, comment='总误差(E)=电子支付实际入账金额+银行存款金额+银行存款手续费-POS机小票里显示的电子支付总金额-POS机小票里显示的现金总金额')

    # 误差字段仅存储，默认0
    cash_difference = db.Column(db.Float, default=0.0, nullable=False, comment='POS现金收入误差(A)，仅存储，默认0')
    electronic_difference = db.Column(db.Float, default=0.0, nullable=False, comment='POS电子支付误差(B)，仅存储，默认0')

    remark = db.Column(db.String(255), comment='备注')

    # 步骤与状态
    pos_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第一步(POS)是否完成')
    takeaway_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='第二步(外卖)是否完成')
    # 实际入账金额录入是否完成（包括电子支付实际入账和银行存款）
    actual_arrival_info_completed = db.Column(db.Boolean, default=False, nullable=False, comment='实际入账金额录入是否完成')
    is_submitted = db.Column(db.Boolean, default=False, nullable=False, comment='是否已最终提交给财务')
    financial_check_status = db.Column(
        db.Enum(FinancialCheckStatus),
        default=FinancialCheckStatus.PENDING,
        nullable=False,
        comment='财务核对状态（仅PENDING/APPROVED）'
    )

    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 附件关联
    attachments = db.relationship('DailySalesAttachments', backref='daily_sale', lazy='dynamic',
                                  cascade="all, delete-orphan")

    def __repr__(self):
        return f'<DailySales {self.report_id} for Store {self.store_id} on {self.report_date}>'

    def auto_calculate(self):
        """
        自动计算理论营业额、实际总营业额、误差等字段。
        公式详见业务表格和字段说明：
        - 店铺理论营业额（T0）= 现金收入 + 电子支付收入 + 外卖收入 + 代金券使用金额
        - 理论营收总金额（T2）= 店铺理论营业额（T0） + 第三方外卖平台收入（T1） - POS机小票里显示的代金券总金额 - 银行存款手续费
        - 实际总营业额(S)=第三方外卖平台收入(T1)+外卖收入+电子支付实际入账金额+银行存款金额
        - 总误差 = 电子支付实际入账金额 + 银行存款金额 + 银行存款手续费 - POS机小票电子支付收入 - POS机小票现金收入
        
        """
        # 店铺理论营业额 T0 = 现金收入 + 电子支付收入 + 外卖收入 + 代金券使用金额
        self.pos_total = (self.cash_income or 0) + (self.pos_income or 0) + (self.day_pass_income or 0) + (self.voucher_amount or 0)
        # 理论营收总金额 T2
        self.theoretical_total = self.pos_total + (self.takeaway_amount or 0) - (self.voucher_amount or 0) - (self.bank_fee or 0)
        # 电子支付实际入账金额 EA 由用户填写，不再自动计算
        # self.electronic_actual_arrival = (self.pos_income or 0) + (self.electronic_difference or 0)
        # 实际总营业额 S = 第三方外卖平台收入(T1) + 外卖收入 + 电子支付实际入账金额 + 银行存款金额
        self.actual_sales = (self.takeaway_amount or 0) + (self.day_pass_income or 0) + (self.electronic_actual_arrival or 0) + (self.bank_deposit or 0)
        # 总误差 E = 电子支付实际入账金额 + 银行存款金额 + 银行存款手续费 - POS机小票电子支付总金额 - POS机小票现金总金额
        self.total_error = (self.electronic_actual_arrival or 0) + (self.bank_deposit or 0) + (self.bank_fee or 0) - (self.pos_income or 0) - (self.cash_income or 0)

    def to_dict(self):
        """
        将 DailySales 对象转换为字典格式，方便API返回。
        """
        return {
            "report_id": self.report_id,
            "store_id": self.store_id,
            "user_id": self.user_id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "cash_income": self.cash_income,
            "pos_income": self.pos_income,
            "day_pass_income": self.day_pass_income,
            "voucher_amount": self.voucher_amount,
            "pos_total": self.pos_total,
            "electronic_actual_arrival": self.electronic_actual_arrival,
            "bank_deposit": self.bank_deposit,
            "bank_fee": self.bank_fee,
            "takeaway_amount": self.takeaway_amount,
            "actual_sales": self.actual_sales,
            "total_error": self.total_error,
            "cash_difference": self.cash_difference,
            "electronic_difference": self.electronic_difference,
            "remark": self.remark,
            "pos_info_completed": self.pos_info_completed,
            "takeaway_info_completed": self.takeaway_info_completed,
            "bank_info_completed": self.bank_info_completed,
            "is_submitted": self.is_submitted,
            "financial_check_status": self.financial_check_status.value if self.financial_check_status else None,
            # "archived": self.archived,  # 已废弃
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "attachments": [attachment.to_dict() for attachment in self.attachments]
        }