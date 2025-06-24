# MXStoreBI/app/models/enums.py

import enum


class RoleType(enum.Enum):
    """
    用户角色枚举 (源自 user.py)
    """
    ADMIN = "admin"            # 管理员
    HEAD_MANAGER = "head_manager"  # 总店长
    FINANCE = "finance"        # 财务
    BRANCH_MANAGER = "branch_manager" # 分店长
    EMPLOYEE = "employee"      # 店员

class AttachmentType(enum.Enum):
    """
    附件类型枚举 (源自 attachment.py)
    """
    sales_slip = "sales_slip"           # 销售小票
    bank_receipt = "bank_receipt"     # 银行凭证
    takeaway_screenshot = "takeaway_screenshot" # 外卖截图
    image = "image"                   # 图片
    pdf = "pdf"                       # PDF文件

class FinancialCheckStatus(enum.Enum):
    """
    财务核对状态的枚举 (新业务逻辑需要)
    """
    PENDING = 'PENDING'                 # 待核对
    BANK_RECEIVED = 'BANK_RECEIVED'     # 现金存款已到账
    TAKEEAWAY_RECEIVED = 'TAKEEAWAY_RECEIVED' # 外卖收入已到账
    AMOUNT_VERIFIED = 'AMOUNT_VERIFIED' # 金额已核实
    REQUIRES_REMEDIATION = 'REQUIRES_REMEDIATION' # 需要补交
    CHECKED = 'CHECKED'                 # 审核通过