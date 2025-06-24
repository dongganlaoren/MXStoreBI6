# MXStoreBI/app/models/attachment.py

from datetime import datetime

from app.extensions import db

# 【核心修改 1】: 从我们统一的 enums.py 文件中导入 AttachmentType
from .enums import AttachmentType


# 注意：根据您的文件内容，原有的模型名为 DailySalesAttachments，我予以保留
class DailySalesAttachments(db.Model):
    """
    营业额上报凭证模型
    """
    __tablename__ = "daily_sales_attachments"

    attachment_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="凭证ID")
    report_id = db.Column(db.Integer, db.ForeignKey("daily_sales.report_id", ondelete="CASCADE"), nullable=False,
                          comment="日报ID")
    file_path = db.Column(db.String(255), nullable=True, comment="文件路径")

    # 【核心修改 2】: 这里的 db.Enum(AttachmentType) 现在使用的是我们从外部导入的枚举
    attachment_type = db.Column(db.Enum(AttachmentType), nullable=False, comment="附件类型")

    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    # 【核心修改 3】: 原本在此文件中的 class AttachmentType(enum.Enum): ... 定义已被删除

    def __repr__(self):
        return f"<DailySalesAttachments {self.attachment_type}>"

    def to_dict(self):
        return {
            "attachment_id": self.attachment_id,
            "report_id": self.report_id,
            "file_path": self.file_path,
            "attachment_type": self.attachment_type.value,
            "created_at": self.created_at.isoformat(),
        }