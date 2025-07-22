# MXStoreBI/app/models/enums.py

from enum import Enum


class RoleType(Enum):
    """用户角色枚举"""

    ADMIN = "ADMIN"
    HEAD_MANAGER = "HEAD_MANAGER"
    FINANCE = "FINANCE"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    EMPLOYEE = "EMPLOYEE"  # 员工


class FinancialCheckStatus(Enum):
    """财务核对状态枚举"""

    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 已通过
    REJECTED = "REJECTED"  # 已拒绝（暂时保留但不使用）


class AttachmentType(Enum):
    """附件类型枚举"""

    sales_slip = "sales_slip"
    bank_receipt = "bank_receipt"
    takeaway_screenshot = "takeaway_screenshot"
    electronic_actual_arrival_receipt = "electronic_actual_arrival_receipt"


class ReimbursementPrimaryCategory(Enum):
    """报销主分类枚举"""

    OFFICE_SUPPLIES = "办公用品"
    TRAVEL_EXPENSES = "差旅费用"
    MARKETING_EXPENSES = "营销费用"
    EQUIPMENT_MAINTENANCE = "设备维护"
    TRAINING_EDUCATION = "培训教育"
    OTHER = "其他"


class ReimbursementStatus(Enum):
    """报销状态枚举"""

    PENDING = "待审核"
    APPROVED = "已通过"
    REJECTED = "已拒绝"
    PAID = "已支付"
