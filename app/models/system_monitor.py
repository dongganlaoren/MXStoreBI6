# app/models/system_monitor.py

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum, Text, Index

from app.extensions import db


class LogLevel(PyEnum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertLevel(PyEnum):
    """告警级别枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(PyEnum):
    """告警状态枚举"""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class SystemLog(db.Model):
    """系统日志模型"""
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    level = db.Column(Enum(LogLevel), nullable=False, index=True)
    logger_name = db.Column(db.String(100), nullable=False, index=True)
    module = db.Column(db.String(100), nullable=True, index=True)
    function_name = db.Column(db.String(100), nullable=True)
    line_number = db.Column(db.Integer, nullable=True)
    message = db.Column(Text, nullable=False)
    exception_info = db.Column(Text, nullable=True)
    request_id = db.Column(db.String(36), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True, index=True)  # 修正外键引用
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    # 创建复合索引
    __table_args__ = (
        Index('idx_timestamp_level', 'timestamp', 'level'),
        Index('idx_logger_timestamp', 'logger_name', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level.value if self.level else None,
            'logger_name': self.logger_name,
            'module': self.module,
            'function_name': self.function_name,
            'line_number': self.line_number,
            'message': self.message,
            'exception_info': self.exception_info,
            'request_id': self.request_id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }


class SystemMetric(db.Model):
    """系统指标模型"""
    __tablename__ = 'system_metrics'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    metric_name = db.Column(db.String(100), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    metric_unit = db.Column(db.String(20), nullable=True)
    tags = db.Column(db.JSON, nullable=True)  # 存储额外的标签信息

    __table_args__ = (
        Index('idx_metric_timestamp', 'metric_name', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'tags': self.tags
        }


class SystemAlert(db.Model):
    """系统告警模型"""
    __tablename__ = 'system_alerts'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    alert_type = db.Column(db.String(50), nullable=False, index=True)
    level = db.Column(Enum(AlertLevel), nullable=False, index=True)
    status = db.Column(Enum(AlertStatus), default=AlertStatus.OPEN, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(Text, nullable=False)
    source_data = db.Column(db.JSON, nullable=True)  # 存储触发告警的原始数据
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)  # 修正外键引用
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'alert_type': self.alert_type,
            'level': self.level.value if self.level else None,
            'status': self.status.value if self.status else None,
            'title': self.title,
            'description': self.description,
            'source_data': self.source_data,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class HealthCheck(db.Model):
    """健康检查记录模型"""
    __tablename__ = 'health_checks'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    check_name = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, index=True)  # OK, WARNING, ERROR
    response_time = db.Column(db.Float, nullable=True)  # 响应时间（毫秒）
    details = db.Column(db.JSON, nullable=True)  # 详细信息

    __table_args__ = (
        Index('idx_check_timestamp', 'check_name', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'check_name': self.check_name,
            'status': self.status,
            'response_time': self.response_time,
            'details': self.details
        }
