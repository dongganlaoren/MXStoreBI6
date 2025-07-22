# app/views/main_views.py

from datetime import date

from flask import Blueprint, current_app, flash, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models import DailySales, RoleType, Store

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
        # 门店组：仅看自己门店；管理组：看全部门店
        if user_role in (RoleType.EMPLOYEE, RoleType.BRANCH_MANAGER):
            if hasattr(current_user, "store_id") and current_user.store_id:
                stores = [Store.query.get(current_user.store_id)]
            else:
                stores = []
        else:
            stores = Store.query.order_by(Store.store_id.asc()).all()

        today = date.today()
        first_day_of_month = date(today.year, today.month, 1)

        # 只统计已审核通过的数据
        from app.models.enums import FinancialCheckStatus

        stats = {}
        daily_reports = {}

        for store in stores:
            if not store:
                continue
            # 判断是否开通外卖平台（假设有字段 store.has_takeaway 或 store.takeaway_enabled）
            has_t1 = getattr(store, "has_takeaway", None)
            if has_t1 is None:
                # 兼容旧模型，若无字段则判断近一年有无外卖数据
                t1_count = (
                    db.session.query(func.count(DailySales.report_id))
                    .filter(
                        DailySales.store_id == store.store_id,
                        DailySales.takeaway_amount is not None,
                        DailySales.takeaway_amount > 0,
                        DailySales.report_date
                        >= date(today.year - 1, today.month, today.day),
                    )
                    .scalar()
                )
                has_t1 = t1_count > 0
            # 本月累计
            t0 = (
                db.session.query(func.sum(DailySales.pos_total))
                .filter(
                    DailySales.store_id == store.store_id,
                    DailySales.report_date >= first_day_of_month,
                    DailySales.financial_check_status
                    == FinancialCheckStatus.APPROVED,
                )
                .scalar()
                or 0
            )
            t1 = None
            if has_t1:
                t1 = (
                    db.session.query(func.sum(DailySales.takeaway_amount))
                    .filter(
                        DailySales.store_id == store.store_id,
                        DailySales.report_date >= first_day_of_month,
                        DailySales.financial_check_status
                        == FinancialCheckStatus.APPROVED,
                    )
                    .scalar()
                    or 0
                )
            actual = (
                db.session.query(func.sum(DailySales.actual_sales))
                .filter(
                    DailySales.store_id == store.store_id,
                    DailySales.report_date >= first_day_of_month,
                    DailySales.financial_check_status
                    == FinancialCheckStatus.APPROVED,
                )
                .scalar()
                or 0
            )
            stats[store.store_id] = {
                "t0": float(t0 or 0),
                "t1": float(t1) if t1 is not None else None,
                "actual": float(actual or 0),
                "has_t1": has_t1,
            }
            # 近一周有审核通过日报（不要求连续）
            last_7_days_q = (
                db.session.query(DailySales.report_date)
                .filter(
                    DailySales.store_id == store.store_id,
                    DailySales.report_date
                    >= today.replace(day=max(1, today.day - 6)),
                    DailySales.report_date <= today,
                    DailySales.financial_check_status
                    == FinancialCheckStatus.APPROVED,
                )
                .group_by(DailySales.report_date)
            )
            last_7_days = [
                r[0]
                for r in last_7_days_q.order_by(
                    DailySales.report_date.desc()
                ).limit(7)
            ]
            reports = []
            for d in reversed(last_7_days):
                day_data = (
                    db.session.query(
                        func.sum(DailySales.pos_total),
                        (
                            func.sum(DailySales.takeaway_amount)
                            if has_t1
                            else None
                        ),
                        func.sum(DailySales.actual_sales),
                        func.sum(DailySales.total_error),
                    )
                    .filter(
                        DailySales.store_id == store.store_id,
                        DailySales.report_date == d,
                        DailySales.financial_check_status
                        == FinancialCheckStatus.APPROVED,
                    )
                    .first()
                )
                reports.append(
                    {
                        "date": d.strftime("%Y-%m-%d"),
                        "t0": float(day_data[0] or 0),
                        "t1": (
                            float(day_data[1])
                            if (has_t1 and day_data[1] is not None)
                            else None
                        ),
                        "actual": float(day_data[2] or 0),
                        "total_error": float(day_data[3] or 0),
                        "has_t1": has_t1,
                    }
                )
            # 若无审核通过日报，补空
            while len(reports) < 7:
                reports.insert(
                    0,
                    {
                        "date": "-",
                        "t0": 0,
                        "t1": None if has_t1 else None,
                        "actual": 0,
                        "total_error": 0,
                        "has_t1": has_t1,
                    },
                )
            daily_reports[store.store_id] = reports

        return render_template(
            "main/index.html",
            stores=stores,
            stats=stats,
            daily_reports=daily_reports,
        )
    except Exception as e:
        current_app.logger.error(f"加载首页时发生错误: {e}")
        flash("加载首页时发生未知错误，请联系管理员。", "danger")
        return render_template(
            "main/index.html", stores=[], cumulative_sales={}
        )
