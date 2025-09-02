# 财务报销相关模型
from datetime import datetime, timezone

from app.extensions import db
from app.models.enums import ReimbursementStatus, ReimbursementAttachmentType, ReimbursementPrimaryCategory, \
    ReimbursementSecondaryCategory, ReimbursementCheckStatus


class ReimbursementRequest(db.Model):
    __tablename__ = 'reimbursement_requests'

    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="报销申请ID")
    submitter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="申请人ID")
    store_id = db.Column(db.String(32), db.ForeignKey('stores.store_id'), nullable=True, comment="关联店铺ID")
    primary_category = db.Column(db.Enum(ReimbursementPrimaryCategory), nullable=False, comment="一级分类")
    secondary_category = db.Column(db.Enum(ReimbursementSecondaryCategory), nullable=False, comment="二级分类")
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment="报销金额")
    currency = db.Column(db.String(8), nullable=False, default='THB', comment="货币单位")
    description = db.Column(db.Text, nullable=True, comment="报销说明")
    status = db.Column(db.Enum(ReimbursementStatus), default=ReimbursementStatus.PENDING, nullable=False,
                       comment="审批状态")
    # 新增：核对状态
    check_status = db.Column(db.Enum(ReimbursementCheckStatus), default=ReimbursementCheckStatus.UNCHECKED,
                             nullable=False, comment="核对状态")
    approval_comments = db.Column(db.Text, nullable=True, comment="审批意见")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False,
                           comment="更新时间")
    approved_at = db.Column(db.DateTime, nullable=True, comment="审批通过时间")
    approver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="审批人ID")

    submitter = db.relationship('User', backref='reimbursement_requests', foreign_keys=[submitter_id])
    store = db.relationship('Store', backref='reimbursement_requests', foreign_keys=[store_id])
    attachments = db.relationship('ReimbursementAttachment', backref='request', lazy='dynamic')
    approver = db.relationship('User', foreign_keys=[approver_id])
    # 新增：抄送人关系
    cc_recipients = db.relationship('ReimbursementCCRecipient', backref='request', lazy='dynamic',
                                    cascade='all, delete-orphan')


class ReimbursementCCRecipient(db.Model):
    """报销申请抄送人表"""
    __tablename__ = 'reimbursement_cc_recipients'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="抄送记录ID")
    request_id = db.Column(db.Integer, db.ForeignKey('reimbursement_requests.request_id'), nullable=False,
                           comment="报销申请ID")
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="抄送人用户ID")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="创建时间")

    # 关联用户信息
    user = db.relationship('User', backref='reimbursement_cc_received', foreign_keys=[user_id])

    # 联合唯一约束，防止同一申请重复抄送给同一人
    __table_args__ = (
        db.UniqueConstraint('request_id', 'user_id', name='uk_request_user_cc'),
    )


class ReimbursementDefaultCCRecipient(db.Model):
    """默认抄送人配置表 - 系统级配置，所有报销申请都会自动抄送给这些人"""
    __tablename__ = 'reimbursement_default_cc_recipients'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="配置记录ID")
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="默认抄送人用户ID")
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="是否启用")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="创建时间")
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="创建人ID")

    # 关联用户信息
    user = db.relationship('User', backref='default_cc_configs', foreign_keys=[user_id])
    creator = db.relationship('User', foreign_keys=[created_by])

    # 唯一约束，防止重复配置同一用户为默认抄送人
    __table_args__ = (
        db.UniqueConstraint('user_id', name='uk_default_cc_user'),
    )


class ReimbursementAttachment(db.Model):
    __tablename__ = 'reimbursement_attachments'

    attachment_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="附件ID")
    request_id = db.Column(db.Integer, db.ForeignKey('reimbursement_requests.request_id'), nullable=False,
                           comment="所属报销申请ID")
    attachment_type = db.Column(db.Enum(ReimbursementAttachmentType), nullable=False, comment="附件类型（提交/审批）")
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="上传人ID")
    original_filename = db.Column(db.String(255), nullable=False, comment="原始文件名")
    file_path = db.Column(db.String(255), nullable=False, comment="文件存储路径")
    file_size = db.Column(db.Integer, nullable=False, comment="文件大小（字节）")
    mime_type = db.Column(db.String(100), nullable=False, comment="文件MIME类型")
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="上传时间")

    uploader = db.relationship('User', backref='reimbursement_attachments', foreign_keys=[uploader_id])
