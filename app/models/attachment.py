# app/models/attachments.py
import enum  # 导入 enum 模块
from datetime import datetime

from app.extensions import db  # 导入数据库实例


class AttachmentType(enum.Enum):
    """
    附件类型枚举
    """
    sales_slip = "sales_slip"  # 销售小票
    bank_receipt = "bank_receipt"  # 银行凭证
    takeaway_screenshot = "takeaway_screenshot"  # 外卖截图
    image = "image"  # 图片
    pdf = "pdf"  # PDF文件


class DailySalesAttachments(db.Model):
    """
    营业额上报凭证模型
    """

    __tablename__ = "daily_sales_attachments"  # 表名

    attachment_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="凭证ID")
    report_id = db.Column(db.Integer, db.ForeignKey("daily_sales.report_id", ondelete="CASCADE"), nullable=False,
                         comment="日报ID")
    file_path = db.Column(db.String(255), nullable=False, comment="文件路径")
    attachment_type = db.Column(db.Enum(AttachmentType), nullable=False, comment="附件类型")  # 使用 AttachmentType 枚举
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<DailySalesAttachments {self.attachment_type}>"  # 返回对象的字符串表示形式

    def to_dict(self):
        """
        将对象转换为字典
        """
        return {
            "attachment_id": self.attachment_id,
            "report_id": self.report_id,
            "file_path": self.file_path,
            "attachment_type": self.attachment_type.value,  # 返回枚举的值
            "created_at": self.created_at,
        }