# MXStoreBI/app/models/enums.py

import enum


class RoleType(enum.Enum):
    """
    用户角色枚举 (源自 user.py)
    """
    ADMIN = "ADMIN"  # 管理员
    HEAD_MANAGER = "HEAD_MANAGER"  # 总店长
    FINANCE = "FINANCE"  # 财务
    BRANCH_MANAGER = "BRANCH_MANAGER"  # 分店长
    EMPLOYEE = "EMPLOYEE"  # 店员


class AttachmentType(enum.Enum):
    """
    附件类型枚举 (源自 attachment.py)
    """
    sales_slip = "sales_slip"  # 销售小票
    bank_receipt = "bank_receipt"  # 银行凭证
    takeaway_screenshot = "takeaway_screenshot"  # 外卖截图
    electronic_actual_arrival_receipt = "electronic_actual_arrival_receipt"  # 电子支付实际入账凭证
    image = "image"  # 图片
    pdf = "pdf"  # PDF文件


class FinancialCheckStatus(enum.Enum):
    """
    财务核对状态的枚举（MVP极简模式，仅保留两个状态）
    """
    PENDING = 'PENDING'  # 待审核
    APPROVED = 'APPROVED'  # 已审核


# 新增：实际到账金额修改历史记录类型
class BankDepositHistoryAction(enum.Enum):
    CREATE = 'CREATE'  # 首次填写
    MODIFY = 'MODIFY'  # 财务或店员修改


# --- (安全新增) 财务报销模块专属枚举 ---

class ReimbursementPrimaryCategory(enum.Enum):
    """
    报销成本一级分类
    """
    SHARED_COST = "公摊成本"
    STORE_COST = "店铺成本"


class ReimbursementSecondaryCategory(enum.Enum):
    """
    报销成本二级分类
    """
    # 公摊成本
    SHARED_REIMBURSEMENT = "公摊报销"
    AGENCY_ACCOUNTING = "代理记账"
    TAXES = "各种税费"
    EMPLOYEE_SOCIAL_SECURITY = "员工社保"
    STORE_MANAGEMENT = "店铺管理"
    OTHER_SHARED_COST = "其它公摊"

    # 店铺成本
    MIXTURE_MATERIAL = "蜜雪物料"
    MATERIAL_TRANSPORT = "物料运输"
    FIXED_SALARY = "固定工资"
    TEMPORARY_SALARY = "临时工工资"
    EXTERNAL_LEMON = "外部柠檬"
    STORE_PETTY_CASH = "店铺备用金"
    RENTAL_TAX = "租房税"
    UTILITIES = "水电费"
    STORE_RENT = "店铺房租"
    WAREHOUSE_RENT = "仓库房租"
    OTHER_COST = "其它成本"


class ReimbursementAttachmentType(enum.Enum):
    """
    报销流程附件类型 (用于区分上传阶段)
    """
    SUBMISSION = "SUBMISSION"
    APPROVAL = "APPROVAL"


class ReimbursementStatus(enum.Enum):
    """
    【新增】报销申请的审批状态
    """
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    DRAFT = 'DRAFT'


class ReimbursementCheckStatus(enum.Enum):
    """
    报销核对状态
    """
    CHECKED = 'CHECKED'  # 已核对
    UNCHECKED = 'UNCHECKED'  # 未核对


# --- 新增：考勤相关枚举 ---
class AttendanceAction(enum.Enum):
    CLOCK_IN = 'CLOCK_IN'  # 上班打卡
    CLOCK_OUT = 'CLOCK_OUT'  # 下班打卡


class AttendanceSource(enum.Enum):
    WEB = 'WEB'
    LINE = 'LINE'
    API = 'API'


# --- 新增：店铺整改模块枚举 ---
class RenovationTaskStatus(enum.Enum):
    """
    整改任务状态枚举
    """
    PENDING = 'PENDING'  # 待处理
    PROCESSING = 'PROCESSING'  # 处理中
    AWAITING_VERIFICATION = 'AWAITING_VERIFICATION'  # 待验收
    COMPLETED = 'COMPLETED'  # 已完成
    CLOSED = 'CLOSED'  # 已关闭
    REJECTED = 'REJECTED'  # 验收不通过


class RenovationTaskPriority(enum.Enum):
    """
    整改任务优先级枚举
    """
    URGENT = 'URGENT'  # 紧急
    HIGH = 'HIGH'  # 高
    MEDIUM = 'MEDIUM'  # 中
    LOW = 'LOW'  # 低


class RenovationTaskCategory(enum.Enum):
    """
    整改任务分类枚举
    """
    HYGIENE = 'HYGIENE'  # 卫生问题
    EQUIPMENT = 'EQUIPMENT'  # 设备维护
    SERVICE = 'SERVICE'  # 服务质量
    SAFETY = 'SAFETY'  # 安全隐患
    OTHER = 'OTHER'  # 其他问题


class RenovationRecordAction(enum.Enum):
    """
    整改记录操作类型枚举
    """
    CREATE = 'CREATE'  # 创建任务
    UPDATE = 'UPDATE'  # 更新状态
    UPLOAD_EVIDENCE = 'UPLOAD_EVIDENCE'  # 上传证据
    SUBMIT_FOR_VERIFICATION = 'SUBMIT_FOR_VERIFICATION'  # 提交验收
    VERIFY = 'VERIFY'  # 验收
    REJECT = 'REJECT'  # 驳回
    CLOSE = 'CLOSE'  # 关闭任务


class VerificationResult(enum.Enum):
    """
    验收结果枚举
    """
    PASSED = 'PASSED'  # 验收通过
    FAILED = 'FAILED'  # 验收不通过


# --- 新增：系统通知模块枚举 ---
class NotificationType(enum.Enum):
    """
    通知类型枚举
    """
    RENOVATION_TASK_ASSIGNED = 'RENOVATION_TASK_ASSIGNED'  # 整改任务分配通知
    RENOVATION_OVERDUE_WARNING = 'RENOVATION_OVERDUE_WARNING'  # 逾期预警通知
    RENOVATION_VERIFICATION_NEEDED = 'RENOVATION_VERIFICATION_NEEDED'  # 验收通知
    RENOVATION_VERIFICATION_RESULT = 'RENOVATION_VERIFICATION_RESULT'  # 结果通知
    REIMBURSEMENT_NOTIFICATION = 'REIMBURSEMENT_NOTIFICATION'  # 报销通知（预留）
    ATTENDANCE_NOTIFICATION = 'ATTENDANCE_NOTIFICATION'  # 考勤通知（预留）
    SYSTEM_NOTIFICATION = 'SYSTEM_NOTIFICATION'  # 系统通知（预留）


class NotificationChannel(enum.Enum):
    """
    通知渠道枚举
    """
    EMAIL = 'EMAIL'  # 邮件
    WEB = 'WEB'  # 站内信
    PUSH = 'PUSH'  # 推送


class NotificationStatus(enum.Enum):
    """
    通知发送状态枚举
    """
    PENDING = 'PENDING'  # 待发送
    SENT = 'SENT'  # 已发送
    FAILED = 'FAILED'  # 发送失败
    RETRY = 'RETRY'  # 重试中
