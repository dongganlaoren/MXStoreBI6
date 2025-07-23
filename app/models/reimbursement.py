# 财务报销相关模型
from datetime import datetime

from app.extensions import db
from app.models.enums import (
    ReimbursementAttachmentType,
    ReimbursementPrimaryCategory,
    ReimbursementSecondaryCategory,
    ReimbursementStatus,
)


class ReimbursementRequest(db.Model):
    __tablename__ = "reimbursement_requests"

    request_id = db.Column(
        db.Integer, primary_key=True, autoincrement=True, comment="报销申请ID"
    )
    submitter_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False,
        comment="申请人ID",
    )
    store_id = db.Column(
        db.String(32),
        db.ForeignKey("stores.store_id"),
        nullable=True,
        comment="关联店铺ID",
    )
    primary_category = db.Column(
        db.Enum(ReimbursementPrimaryCategory),
        nullable=False,
        comment="一级分类",
    )
    secondary_category = db.Column(
        db.Enum(ReimbursementSecondaryCategory),
        nullable=False,
        comment="二级分类",
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment="报销金额")
    currency = db.Column(
        db.String(8), nullable=False, default="THB", comment="货币单位"
    )
    description = db.Column(db.Text, nullable=True, comment="报销说明")
    status = db.Column(
        db.Enum(ReimbursementStatus),
        default=ReimbursementStatus.PENDING,
        nullable=False,
        comment="审批状态",
    )
    approval_comments = db.Column(db.Text, nullable=True, comment="审批意见")
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间",
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )
    approved_at = db.Column(db.DateTime, nullable=True, comment="审批通过时间")
    approver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False,
        comment="审批人ID",
    )

    submitter = db.relationship(
        "User", backref="reimbursement_requests", foreign_keys=[submitter_id]
    )
    store = db.relationship(
        "Store", backref="reimbursement_requests", foreign_keys=[store_id]
    )
    attachments = db.relationship(
        "ReimbursementAttachment", backref="request", lazy="dynamic"
    )
    approver = db.relationship("User", foreign_keys=[approver_id])


class ReimbursementAttachment(db.Model):
    __tablename__ = "reimbursement_attachments"

    attachment_id = db.Column(
        db.Integer, primary_key=True, autoincrement=True, comment="附件ID"
    )
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("reimbursement_requests.request_id"),
        nullable=False,
        comment="报销申请ID",
    )
    attachment_type = db.Column(
        db.Enum(ReimbursementAttachmentType),
        nullable=False,
        comment="附件类型",
    )
    file_path = db.Column(db.String(255), nullable=False, comment="文件路径")
    original_filename = db.Column(
        db.String(255), nullable=True, comment="原始文件名"
    )
    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="上传时间",
    )

# 兼容性导出 Reimbursement
Reimbursement = ReimbursementRequest
