# app/models/email_task_log.py
import enum
from datetime import datetime

from app.extensions import db


class EmailTaskType(enum.Enum):
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'


class EmailTaskStatus(enum.Enum):
    success = 'success'
    partial_fail = 'partial_fail'
    fail = 'fail'


class EmailTaskLog(db.Model):
    """
    邮件任务日志表
    记录销售汇总信息邮件发送任务的执行情况
    """
    __tablename__ = 'email_task_log'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_type = db.Column(db.Enum(EmailTaskType), nullable=False, comment='任务类型')
    start_date = db.Column(db.Date, nullable=False, comment='数据统计开始时间')
    end_date = db.Column(db.Date, nullable=False, comment='数据统计结束时间')
    recipients = db.Column(db.Text, nullable=False, comment='收件人邮箱列表（逗号分隔）')
    status = db.Column(db.Enum(EmailTaskStatus), nullable=False, comment='发送结果状态')
    success_count = db.Column(db.Integer, default=0, nullable=False, comment='成功发送数量')
    fail_count = db.Column(db.Integer, default=0, nullable=False, comment='失败数量')
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment='更新时间')

    def __repr__(self):
        return f'<EmailTaskLog {self.id} {self.task_type.value} {self.status.value}>'

    def to_dict(self):
        return {
            'id': self.id,
            'task_type': self.task_type.value if self.task_type else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'recipients': self.recipients,
            'status': self.status.value if self.status else None,
            'success_count': self.success_count,
            'fail_count': self.fail_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
