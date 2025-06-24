# app/views/main_views.py

from datetime import date

# 【核心修正】: 我们将导入语句拆分，从正确的地方导入各自的模块
# 1. 从 app.extensions 导入 db 数据库实例
from app.extensions import db

# 2. 从 app.models (也就是 __init__.py) 统一导入所有需要的模型和枚举
from app.models import DailySales, RoleType, Store, StoreStaff
from flask import Blueprint, current_app, flash, render_template
from flask_login import current_user, login_required
from sqlalchemy import func, literal

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@login_required
def index():
    """
    主页面视图：展示当前用户可见的门店信息及本月累计营业额
    """
    try:
        user_role = current_user.role
        stores = []

        if user_role in (RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER):
            staff = StoreStaff.query.filter_by(user_id=current_user.user_id).first()
            if staff:
                stores = [Store.query.get(staff.store_id)]
        else:
            stores = Store.query.all()

        today = date.today()
        first_day_of_month = date(today.year, today.month, 1)

        last_archived_sales = {}
        cumulative_sales = {}

        for store in stores:
            if not store: continue

            latest_sale = DailySales.query.filter(
                DailySales.store_id == store.store_id,
                DailySales.archived == True
            ).order_by(DailySales.report_date.desc()).first()

            if latest_sale:
                calculated_actual_sales = (latest_sale.bank_deposit or 0) + (latest_sale.voucher_amount or 0)
                last_archived_sales[store.store_id] = {
                    "report_date": latest_sale.report_date,
                    "actual_sales": calculated_actual_sales
                }
            else:
                last_archived_sales[store.store_id] = None

            total = db.session.query(
                func.sum(literal(0) + DailySales.bank_deposit + DailySales.voucher_amount)
            ).filter(
                DailySales.store_id == store.store_id,
                DailySales.report_date >= first_day_of_month,
                DailySales.archived == True
            ).scalar()
            cumulative_sales[store.store_id] = total or 0

        current_app.logger.info(f"用户 {current_user.username} 成功加载首页。")

        return render_template(
            "main/index.html",
            stores=stores,
            last_archived_sales=last_archived_sales,
            cumulative_sales=cumulative_sales
        )
    except Exception as e:
        current_app.logger.error(f"加载首页时发生错误: {e}", exc_info=True)
        flash("加载首页时发生未知错误，请联系管理员。", "danger")
        return render_template("main/index.html", stores=[], last_archived_sales={}, cumulative_sales={})