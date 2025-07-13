# app/views/main_views.py

from datetime import date
from app.extensions import db
from app.models import DailySales, RoleType, Store, user
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
            if hasattr(current_user, 'store_id') and current_user.store_id:
                stores = [Store.query.get(current_user.store_id)]
            else:
                stores = []
        else:
            stores = Store.query.all()

        today = date.today()
        first_day_of_month = date(today.year, today.month, 1)

        cumulative_sales = {}
        for store in stores:
            if not store:
                continue
            total = db.session.query(
                func.sum(literal(0) + DailySales.bank_deposit + DailySales.voucher_amount)
            ).filter(
                DailySales.store_id == store.store_id,
                DailySales.report_date >= first_day_of_month
            ).scalar()
            cumulative_sales[store.store_id] = total or 0

        current_app.logger.info(f"用户 {current_user.username} 成功加载首页。")

        return render_template(
            "main/index.html",
            stores=stores,
            # last_archived_sales=last_archived_sales,  # archived相关逻辑已废弃
            cumulative_sales=cumulative_sales
        )
    except Exception as e:
        current_app.logger.error(f"加载首页时发生错误: {e}", exc_info=True)
        flash("加载首页时发生未知错误，请联系管理员。", "danger")
        return render_template("main/index.html", stores=[], cumulative_sales={})