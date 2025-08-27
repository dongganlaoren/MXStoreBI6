# MXStoreBI/app/models/__init__.py

# 从 enums.py 中导出所有的枚举类，方便其他地方统一调用
from .attachment import DailySalesAttachments
from .bank_deposit_history import BankDepositHistory
from .daily_sales import DailySales
from .email_task_log import EmailTaskLog, EmailTaskType, EmailTaskStatus
from .enums import AttachmentType, FinancialCheckStatus, RoleType
from .store import Store
# 监控相关模型已移除
# from .system_monitor import (
#     SystemLog, SystemMetric, SystemAlert, HealthCheck,
#     LogLevel, AlertLevel, AlertStatus
# )
# 从各个模型文件中导出核心的模型类
from .user import User

# 清理说明：
# 1. 监控相关模型和枚举已彻底移除。
# 2. 仅保留与业务相关的模型导出。
