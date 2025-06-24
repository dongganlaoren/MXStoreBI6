# MXStoreBI/app/models/__init__.py

# 从 enums.py 中导出所有的枚举类，方便其他地方统一调用
from .attachment import DailySalesAttachments
from .daily_sales import DailySales
from .enums import AttachmentType, FinancialCheckStatus, RoleType
from .store import Store
from .store_staff import StoreStaff

# 从各个模型文件中导出核心的模型类
from .user import User

# 清理说明：
# 1. 我们不再从 daily_sales.py 和 user.py 中导入它们内部的枚举，因为这些定义已被移走。
# 2. 所有需要被外部使用的类和枚举都在这里被统一导出，结构非常清晰。
# 3. 旧的 ReportStatus 枚举已被彻底废弃。
