# app/models/__init__.py
from .attachment import DailySalesAttachments
from .daily_sales import DailySales, FinancialCheckStatus, ReportStatus  # 添加状态类
from .store import Store
from .store_staff import StoreStaff
from .user import RoleType, User  # 添加RoleType
