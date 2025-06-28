# app/models/attachment.py

from datetime import datetime
from flask import current_app
from app.extensions import db
from .enums import AttachmentType


class DailySalesAttachments(db.Model):
    """
    营业额上报凭证模型
    用于存储每条营业日报相关的所有附件（如小票、银行回单、外卖截图等）
    """
    __tablename__ = "daily_sales_attachments"

    attachment_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="凭证ID")
    report_id = db.Column(db.Integer, db.ForeignKey("daily_sales.report_id", ondelete="CASCADE"), nullable=False,
                          comment="日报ID")
    file_path = db.Column(db.String(255), nullable=True, comment="文件路径（本地磁盘，含user_id/store_id/report_date）")
    attachment_type = db.Column(db.Enum(AttachmentType), nullable=False, comment="附件类型（小票/银行/外卖/图片/PDF等）")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        # 日志记录示例
        current_app.logger.info(f"[附件模型] 查询凭证: id={self.attachment_id}, 类型={self.attachment_type}")
        return f"<DailySalesAttachments {self.attachment_type}>"

    def to_dict(self):
        """
        转换为字典，便于API返回和前端展示
        """
        current_app.logger.debug(f"[附件模型] to_dict: {self.attachment_id}")
        return {
            "attachment_id": self.attachment_id,
            "report_id": self.report_id,
            "file_path": self.file_path,
            "attachment_type": self.attachment_type.value,
            "created_at": self.created_at.isoformat(),
        }