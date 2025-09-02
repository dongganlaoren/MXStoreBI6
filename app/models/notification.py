# app/models/notification.py
from datetime import datetime

from app.extensions import db
from app.models.enums import NotificationType, NotificationStatus


class NotificationConfig(db.Model):
    """
    通知配置表
    """
    __tablename__ = "notification_config"

    id = db.Column(db.Integer, primary_key=True, comment="配置ID")
    notification_type = db.Column(db.Enum(NotificationType), nullable=False, comment="通知类型")
    module_name = db.Column(db.String(50), nullable=False, comment="模块名称")
    receiver_rules = db.Column(db.Text, comment="接收人规则（JSON格式）")
    channels = db.Column(db.String(255), comment="发送渠道（逗号分隔）")
    template_id = db.Column(db.Integer, db.ForeignKey('notification_templates.id'), comment="通知模板ID")
    is_enabled = db.Column(db.Boolean, default=True, comment="启用状态")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联
    template = db.relationship('NotificationTemplate', backref='configs')

    def __repr__(self):
        return f"<NotificationConfig {self.notification_type.value}>"

    def to_dict(self):
        return {
            "id": self.id,
            "notification_type": self.notification_type.value,
            "module_name": self.module_name,
            "receiver_rules": self.receiver_rules,
            "channels": self.channels,
            "template_id": self.template_id,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationTask(db.Model):
    """
    通知任务表
    """
    __tablename__ = "notification_tasks"

    id = db.Column(db.Integer, primary_key=True, comment="任务ID")
    notification_type = db.Column(db.Enum(NotificationType), nullable=False, comment="通知类型")
    related_object_id = db.Column(db.String(100), comment="关联对象ID")
    module_name = db.Column(db.String(50), nullable=False, comment="关联模块")
    receivers = db.Column(db.Text, comment="接收人列表（JSON格式）")
    channels = db.Column(db.String(255), comment="发送渠道")
    title = db.Column(db.String(255), comment="通知标题")
    content = db.Column(db.Text, comment="通知内容")
    status = db.Column(db.Enum(NotificationStatus), default=NotificationStatus.PENDING, comment="发送状态")
    send_time = db.Column(db.DateTime, comment="发送时间")
    retry_count = db.Column(db.Integer, default=0, comment="重试次数")
    error_message = db.Column(db.Text, comment="错误信息")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<NotificationTask {self.id} - {self.notification_type.value}>"

    def to_dict(self):
        return {
            "id": self.id,
            "notification_type": self.notification_type.value,
            "related_object_id": self.related_object_id,
            "module_name": self.module_name,
            "receivers": self.receivers,
            "channels": self.channels,
            "title": self.title,
            "content": self.content,
            "status": self.status.value,
            "send_time": self.send_time.isoformat() if self.send_time else None,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationTemplate(db.Model):
    """
    通知模板表
    """
    __tablename__ = "notification_templates"

    id = db.Column(db.Integer, primary_key=True, comment="模板ID")
    notification_type = db.Column(db.Enum(NotificationType), nullable=False, comment="通知类型")
    language = db.Column(db.String(10), default='zh', comment="语言（zh/th）")
    title_template = db.Column(db.String(255), comment="标题模板")
    content_template = db.Column(db.Text, comment="内容模板")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<NotificationTemplate {self.notification_type.value} - {self.language}>"

    def to_dict(self):
        return {
            "id": self.id,
            "notification_type": self.notification_type.value,
            "language": self.language,
            "title_template": self.title_template,
            "content_template": self.content_template,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
