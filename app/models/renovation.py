# app/models/renovation.py
from datetime import datetime

from app.extensions import db
from app.models.enums import (
    RenovationTaskStatus, RenovationTaskPriority, RenovationRecordAction, VerificationResult
)


class RenovationCategory(db.Model):
    """
    整改分类表
    """
    __tablename__ = "renovation_categories"

    id = db.Column(db.Integer, primary_key=True, comment="分类ID")
    name = db.Column(db.String(100), nullable=False, comment="分类名称")
    parent_id = db.Column(db.Integer, db.ForeignKey('renovation_categories.id'), comment="父分类ID")
    description = db.Column(db.Text, comment="分类描述")
    sort_order = db.Column(db.Integer, default=0, comment="排序权重")
    is_active = db.Column(db.Boolean, default=True, comment="是否启用")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联
    children = db.relationship('RenovationCategory', backref=db.backref('parent', remote_side=[id]))
    tasks = db.relationship('RenovationTask', backref='category')

    def __repr__(self):
        return f"<RenovationCategory {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "description": self.description,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RenovationTask(db.Model):
    """
    整改任务表
    """
    __tablename__ = "renovation_tasks"

    id = db.Column(db.Integer, primary_key=True, comment="任务ID")
    title = db.Column(db.String(255), nullable=False, comment="任务标题")
    description = db.Column(db.Text, comment="问题描述")
    category_id = db.Column(db.Integer, db.ForeignKey('renovation_categories.id'), comment="分类ID")
    priority = db.Column(db.Enum(RenovationTaskPriority), default=RenovationTaskPriority.MEDIUM, comment="优先级")
    status = db.Column(db.Enum(RenovationTaskStatus), default=RenovationTaskStatus.PENDING, comment="任务状态")

    # 关联店铺和人员 - 修正外键引用为 users.user_id
    store_id = db.Column(db.String(32), db.ForeignKey('stores.store_id'), nullable=False, comment="责任店铺ID")
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="创建人ID")
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.user_id'), comment="负责人ID（店长）")
    verifier_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), comment="验收人ID（默认总店长）")

    # 时间相关
    due_date = db.Column(db.DateTime, comment="截止时间")
    started_at = db.Column(db.DateTime, comment="开始处理时间")
    completed_at = db.Column(db.DateTime, comment="完成时间")
    verified_at = db.Column(db.DateTime, comment="验收时间")
    closed_at = db.Column(db.DateTime, comment="关闭时间")

    # 验收相关
    verification_result = db.Column(db.Enum(VerificationResult), comment="验收结果")
    verification_comments = db.Column(db.Text, comment="验收意见")

    # 系统字段
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联 - 修正外键引用
    store = db.relationship('Store', backref='renovation_tasks')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_renovation_tasks')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_renovation_tasks')
    verifier = db.relationship('User', foreign_keys=[verifier_id], backref='verified_renovation_tasks')

    # 一对多关联
    records = db.relationship('RenovationRecord', backref='task', cascade='all, delete-orphan')
    attachments = db.relationship('RenovationAttachment', backref='task', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<RenovationTask {self.id} - {self.title}>"

    @property
    def is_overdue(self):
        """判断任务是否已逾期"""
        if not self.due_date or self.status in [RenovationTaskStatus.COMPLETED, RenovationTaskStatus.CLOSED]:
            return False
        return datetime.utcnow() > self.due_date

    @property
    def days_remaining(self):
        """计算剩余天数"""
        if not self.due_date:
            return None
        if self.status in [RenovationTaskStatus.COMPLETED, RenovationTaskStatus.CLOSED]:
            return 0
        delta = self.due_date - datetime.utcnow()
        return max(0, delta.days)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "priority": self.priority.value,
            "status": self.status.value,
            "store_id": self.store_id,
            "store_name": self.store.store_name if self.store else None,
            "created_by": self.created_by,
            "creator_name": self.creator.real_name if self.creator else None,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.real_name if self.assignee else None,
            "verifier_id": self.verifier_id,
            "verifier_name": self.verifier.real_name if self.verifier else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "verification_result": self.verification_result.value if self.verification_result else None,
            "verification_comments": self.verification_comments,
            "is_overdue": self.is_overdue,
            "days_remaining": self.days_remaining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RenovationRecord(db.Model):
    """
    整改记录表
    """
    __tablename__ = "renovation_records"

    id = db.Column(db.Integer, primary_key=True, comment="记录ID")
    task_id = db.Column(db.Integer, db.ForeignKey('renovation_tasks.id'), nullable=False, comment="任务ID")
    action = db.Column(db.Enum(RenovationRecordAction), nullable=False, comment="操作类型")
    content = db.Column(db.Text, comment="操作内容")
    operator_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="操作人ID")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="操作时间")

    # 关联
    operator = db.relationship('User', backref='renovation_records')

    def __repr__(self):
        return f"<RenovationRecord {self.id} - {self.action.value}>"

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "action": self.action.value,
            "content": self.content,
            "operator_id": self.operator_id,
            "operator_name": self.operator.real_name if self.operator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RenovationAttachment(db.Model):
    """
    整改附件表
    """
    __tablename__ = "renovation_attachments"

    id = db.Column(db.Integer, primary_key=True, comment="附件ID")
    task_id = db.Column(db.Integer, db.ForeignKey('renovation_tasks.id'), nullable=False, comment="任务ID")
    file_name = db.Column(db.String(255), nullable=False, comment="文件名")
    file_path = db.Column(db.String(500), nullable=False, comment="文件路径")
    file_type = db.Column(db.String(50), comment="文件类型")
    file_size = db.Column(db.Integer, comment="文件大小（字节）")
    description = db.Column(db.String(255), comment="文件描述")
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, comment="上传人ID")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="上传时间")

    # 关联
    uploader = db.relationship('User', backref='renovation_attachments')

    def __repr__(self):
        return f"<RenovationAttachment {self.file_name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "description": self.description,
            "uploaded_by": self.uploaded_by,
            "uploader_name": self.uploader.real_name if self.uploader else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
