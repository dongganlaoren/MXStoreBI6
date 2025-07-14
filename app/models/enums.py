# MXStoreBI/app/models/enums.py

import enum


class RoleType(enum.Enum):
    """
    用户角色枚举 (源自 user.py)
    """
    ADMIN = "ADMIN"            # 管理员
    HEAD_MANAGER = "HEAD_MANAGER"  # 总店长
    FINANCE = "FINANCE"        # 财务
    BRANCH_MANAGER = "BRANCH_MANAGER" # 分店长
    EMPLOYEE = "EMPLOYEE"      # 店员

class AttachmentType(enum.Enum):
    """
    附件类型枚举 (源自 attachment.py)
    """
    sales_slip = "sales_slip"           # 销售小票
    bank_receipt = "bank_receipt"     # 银行凭证
    takeaway_screenshot = "takeaway_screenshot" # 外卖截图
    electronic_actual_arrival_receipt = "electronic_actual_arrival_receipt" # 电子支付实际入账凭证
    image = "image"                   # 图片
    pdf = "pdf"                       # PDF文件

class FinancialCheckStatus(enum.Enum):
    """
    财务核对状态的枚举（MVP极简模式，仅保留两个状态）
    """
    PENDING = 'PENDING'     # 待审核
    APPROVED = 'APPROVED'   # 已审核


# 新增：实际到账金额修改历史记录类型
class BankDepositHistoryAction(enum.Enum):
    CREATE = 'CREATE'   # 首次填写
    MODIFY = 'MODIFY'   # 财务或店员修改