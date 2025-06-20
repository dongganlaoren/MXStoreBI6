# app/models/daily_sales.py
import enum

from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class ReportStatus(enum.Enum):
    """
    上报状态枚举
    """
    DRAFT_POS = "DRAFT_POS"  # 已保存POS机小票信息草稿
    DRAFT_TAKEAWAY = "DRAFT_TAKEAWAY"  # 已保存第三方外卖平台收入信息草稿
    DRAFT_BANK = "DRAFT_BANK"  # 已保存银行存款信息草稿
    COMPLETED_INFO = "COMPLETED_INFO"  # 营业信息已完成上传 (POS机小票信息已上传)
    COMPLETED_BANK = "COMPLETED_BANK"  # 现金存款凭证已上传
    COMPLETED_TAKEEAWAY = "COMPLETED_TAKEEAWAY"  # 第三方外卖平台销售信息已完成上传
    SUBMITTED = "SUBMITTED"  # 已提交


class FinancialCheckStatus(enum.Enum):
    """
    财务核对状态枚举
    """
    PENDING = "PENDING"  # 待核对
    BANK_RECEIVED = "BANK_RECEIVED"  # 现金存款已到账
    TAKEEAWAY_RECEIVED = "TAKEEAWAY_RECEIVED"  # 第三方外卖平台收入已到账
    AMOUNT_VERIFIED = "AMOUNT_VERIFIED"  # 实际到账金额已核实无误
    REQUIRES_REMEDIATION = "REQUIRES_REMEDIATION"  # 需要补交
    CHECKED = "CHECKED"  # 审核通过


class DailySales(db.Model):
    """
    营业额日报模型
    """

    __tablename__ = "daily_sales"  # 表名

    report_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="报表ID")
    store_id = db.Column(db.String(32), db.ForeignKey("stores.store_id", ondelete="RESTRICT"), nullable=False,
                         comment="店铺ID")
    report_date = db.Column(db.Date, nullable=False, comment="报表日期")

    # 收入类
    total_income = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="POS机小票总收入 (T)")
    cash_sales = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="现金收入 (C)")
    electronic_sales = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="电子支付收入 (P)")
    system_takeaway_sales = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="POS机外卖收入 (D)")
    takeaway_platform_sales = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="第三方外卖平台收入 (Q2)") # 补全字段

    # 误差类
    cash_difference = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="现金误差 (A)")
    electronic_difference = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="电子支付误差 (B)")

    # 财务相关
    voucher_amount = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="代金券使用金额 (R)")
    bank_fee = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="银行手续费 (F)")
    bank_deposit = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="实际到账金额")  # 银行实际收到的金额
    actual_sales = db.Column(db.Numeric(18, 2), nullable=True, default=0, comment="店铺实际营业额")  # 实际营业额，包括代金券

    # 状态字段
    report_status = db.Column(db.Enum(ReportStatus), default=ReportStatus.DRAFT_POS, comment="上报状态")
    financial_check_status = db.Column(db.Enum(FinancialCheckStatus), default=FinancialCheckStatus.PENDING,
                                       comment="财务核对状态")
    archived = db.Column(db.Boolean, default=False, comment="是否已归档")

    # 审计字段
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True, comment="创建人")
    created_at = db.Column(db.DateTime, server_default=func.now(), comment="创建时间")
    modified_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True, comment="最后修改人")
    modified_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now(), comment="修改时间")

    # 关系映射
    store = relationship("Store", backref=db.backref("daily_sales_list", lazy=True))
    creator = relationship("User", foreign_keys=[created_by], backref="created_sales_records")
    modifier = relationship("User", foreign_keys=[modified_by], backref="modified_sales_records")

    def __repr__(self):
        return f"<DailySales {self.report_date} - {self.store_id}>"  # 返回对象的字符串表示形式

    def to_dict(self):
        """
        将对象转换为字典
        """
        return {
            "report_id": self.report_id,
            "store_id": self.store_id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "total_income": self.total_income,
            "cash_sales": self.cash_sales,
            "electronic_sales": self.electronic_sales,
            "system_takeaway_sales": self.system_takeaway_sales,
            "takeaway_platform_sales": self.takeaway_platform_sales,
            "cash_difference": self.cash_difference,
            "electronic_difference": self.electronic_difference,
            "voucher_amount": self.voucher_amount,
            "bank_fee": self.bank_fee,
            "bank_deposit": self.bank_deposit,  # 实际到账金额
            "actual_sales": self.actual_sales,  # 实际营业额
            "report_status": self.report_status.value if self.report_status else None,  # 明确显示枚举值
            "financial_check_status": self.financial_check_status.value if self.financial_check_status else None,
            # 明确显示枚举值
            "archived": self.archived,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_by": self.modified_by,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "calculated_sales": float(self.calculated_sales) if self.calculated_sales is not None else None,
            # 如果 calculated_sales 为 None，则返回 None
        }

    @property
    def calculated_sales(self):
        """
        计算店铺实际营业额
        """
        return self.bank_deposit + self.voucher_amount