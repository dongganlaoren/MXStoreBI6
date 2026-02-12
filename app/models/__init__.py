# MXStoreBI/app/models/__init__.py
"""
集中导出应用内常用的模型与枚举，便于通过
	from app.models import Foo, Bar
的方式统一引用。

注意：仅导出业务相关模型与当前项目使用到的枚举。
"""

# inventory-stocktake 子系统模型
from app.inventory_stocktake.models import MXMaterialInfo, MXInventoryCheck
from .attachment import DailySalesAttachments
from .attendance import AttendanceRecord
from .bank_deposit_history import BankDepositHistory
from .cg_bank_statement import CgBankStatementFile, CgBankStatementTxn
from .daily_sales import DailySales
from .email_report_config import EmailReportConfig
# 邮件任务日志
from .email_task_log import EmailTaskLog, EmailTaskType, EmailTaskStatus
# 统一导出所有在项目中使用到的枚举
from .enums import (
    RoleType,
    AttachmentType,
    FinancialCheckStatus,
    BankDepositHistoryAction,
    ReimbursementPrimaryCategory,
    ReimbursementSecondaryCategory,
    ReimbursementAttachmentType,
    ReimbursementStatus,
    ReimbursementCheckStatus,
    AttendanceAction,
    AttendanceSource,
    RenovationTaskStatus,
    RenovationTaskPriority,
    RenovationRecordAction,
    VerificationResult,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)
from .notification import (
    NotificationConfig,
    NotificationTask,
    NotificationTemplate,
)
# 报销相关模型
from .reimbursement import (
    ReimbursementRequest,
    ReimbursementAttachment,
    ReimbursementCCRecipient,
    ReimbursementDefaultCCRecipient,
)
# 整改与通知相关模型（如后续使用，可直接从此处导出）
from .renovation import (
    RenovationCategory,
    RenovationTask,
    RenovationRecord,
    RenovationAttachment as RenovationAttachmentModel,  # 避免与报销附件名冲突
)
# 核心业务模型
from .store import Store
from .user import User

__all__ = [
    # 模型
    "Store",
    "User",
    "DailySales",
    "DailySalesAttachments",
    "BankDepositHistory",
    "AttendanceRecord",
    "EmailReportConfig",
    # inventory-stocktake
    "MXMaterialInfo",
    "MXInventoryCheck",
    # 报销
    "ReimbursementRequest",
    "ReimbursementAttachment",
    "ReimbursementCCRecipient",
    "ReimbursementDefaultCCRecipient",
    # 整改与通知
    "RenovationCategory",
    "RenovationTask",
    "RenovationRecord",
    "RenovationAttachmentModel",
    "NotificationConfig",
    "NotificationTask",
    "NotificationTemplate",
    # 邮件任务日志
    "EmailTaskLog",
    "EmailTaskType",
    "EmailTaskStatus",

    # 成本治理：银行流水
    "CgBankStatementFile",
    "CgBankStatementTxn",

    # 枚举
    "RoleType",
    "AttachmentType",
    "FinancialCheckStatus",
    "BankDepositHistoryAction",
    "ReimbursementPrimaryCategory",
    "ReimbursementSecondaryCategory",
    "ReimbursementAttachmentType",
    "ReimbursementStatus",
    "ReimbursementCheckStatus",
    "AttendanceAction",
    "AttendanceSource",
    "RenovationTaskStatus",
    "RenovationTaskPriority",
    "RenovationRecordAction",
    "VerificationResult",
    "NotificationType",
    "NotificationChannel",
    "NotificationStatus",
]
