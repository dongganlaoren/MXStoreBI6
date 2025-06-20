# app/views/main_views.py

from datetime import date

from app.extensions import db
from app.models.daily_sales import DailySales
from app.models.store import Store
from app.models.store_staff import StoreStaff
from app.models.user import RoleType
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@login_required
def index():
    """
    主页面视图：展示当前用户可见的门店信息及本月累计营业额
    """
    user_role = current_user.role

    if user_role in (RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER):
        staff = StoreStaff.query.filter_by(user_id=current_user.user_id).first()
        stores = [Store.query.get(staff.store_id)] if staff else []
    else:
        stores = Store.query.all()

    today = date.today()
    first_day = date(today.year, today.month, 1)

    last_archived_sales = {}
    cumulative_sales = {}

    for store in stores:
        latest = DailySales.query.filter_by(store_id=store.store_id, archived=True)\
            .order_by(DailySales.report_date.desc()).first()
        last_archived_sales[store.store_id] = {
            "report_date": latest.report_date,
            "actual_sales": latest.actual_sales
        } if latest else None

        total = db.session.query(func.sum(DailySales.actual_sales))\
            .filter(DailySales.store_id == store.store_id,
                    DailySales.report_date >= first_day,
                    DailySales.archived == True)\
            .scalar()
        cumulative_sales[store.store_id] = total or 0

    return render_template(
        "main/index.html",
        user_role=user_role,
        stores=stores,
        last_archived_sales=last_archived_sales,
        cumulative_sales=cumulative_sales
    )
