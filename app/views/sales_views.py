# app/views/sales_views.py

from datetime import datetime

from app.extensions import db

# 【核心修正】: 将导入的表单名从 DailySalesForm 改为 SalesForm，以匹配实际的类名
from app.forms.sales_forms import SalesForm

# 从模型中导入需要的类
from app.models import DailySales, FinancialCheckStatus, RoleType, Store, User
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_sales():
    """
    统一处理营业信息上报的GET和POST请求。
    """
    # 【核心修正】: 使用正确的表单类名
    form = SalesForm()

    # --- 【全新权限逻辑】: 根据用户角色动态获取其能操作的店铺列表 ---
    if current_user.role in [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]:
        # 管理组用户可以查看和选择所有店铺
        user_stores = Store.query.order_by(Store.store_name).all()
    elif current_user.store_id:
        # 门店组用户（必须有关联的 store_id），只能看到自己的店铺
        user_stores = Store.query.filter_by(store_id=current_user.store_id).all()
    else:
        # 异常情况：一个门店组用户没有关联店铺
        user_stores = []
        flash('您的账户未关联任何店铺，无法上报数据，请联系管理员。', 'warning')
        current_app.logger.warning(f"门店组用户 {current_user.username} (ID: {current_user.user_id}) 未关联店铺。")

    # 将获取到的店铺列表填充到表单的下拉选项中
    form.store_id.choices = [(s.store_id, s.store_name) for s in user_stores]

    if form.validate_on_submit():
        try:
            # 查找或创建日报对象
            daily_sales = DailySales.query.filter_by(
                store_id=form.store_id.data,
                report_date=form.report_date.data
            ).first()

            if daily_sales is None:
                # 如果记录不存在，则创建新的实例
                daily_sales = DailySales(user_id=current_user.user_id)
                db.session.add(daily_sales)
                flash('新的日报已创建，数据已保存！', 'success')
            else:
                # 如果日报已最终提交，则不允许修改
                if daily_sales.is_submitted:
                    flash('该日报已最终提交，无法修改。', 'warning')
                    return redirect(
                        url_for('sales.report_sales', report_date=daily_sales.report_date.strftime('%Y-%m-%d'),
                                store_id=daily_sales.store_id))
                flash('日报数据更新成功！', 'success')

            # 使用 populate_obj 将表单数据填充到模型对象
            form.populate_obj(daily_sales)

            # 提交数据库，将更改保存
            db.session.commit()
            current_app.logger.info(
                f"用户 {current_user.username} 成功保存了店铺 {daily_sales.store_id} "
                f"在 {daily_sales.report_date} 的销售日报。"
            )
            # 操作完成后，重定向回同一页面，保持上下文
            return redirect(url_for('sales.report_sales', report_date=daily_sales.report_date.strftime('%Y-%m-%d'),
                                    store_id=daily_sales.store_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"保存销售日报时发生错误: {e}", exc_info=True)
            flash('保存日报时发生未知错误，请联系管理员。', 'danger')

    # --- GET 请求处理逻辑 (加载页面时) ---
    if not form.is_submitted():
        selected_store_id = request.args.get('store_id', user_stores[0].store_id if user_stores else None)
        selected_date_str = request.args.get('report_date', datetime.today().strftime('%Y-%m-%d'))

        if selected_store_id and selected_date_str:
            form.store_id.data = selected_store_id
            form.report_date.data = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

            existing_report = DailySales.query.filter_by(
                store_id=selected_store_id,
                report_date=form.report_date.data
            ).first()

            if existing_report:
                # 如果找到了记录，用它的数据预填充表单
                form.process(obj=existing_report)

    return render_template('sales/report.html', form=form, title="上报营业额")


@sales_bp.route('/reports/all')
@login_required
def view_all_reports():
    """
    查看所有销售报告的页面（示例）
    """
    if current_user.role != RoleType.ADMIN:
        flash("您没有权限访问此页面。", "warning")
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    pagination = DailySales.query.order_by(DailySales.report_date.desc()).paginate(
        page=page, per_page=current_app.config['RECORDS_PER_PAGE'], error_out=False
    )
    reports = pagination.items

    return render_template('sales/all_reports.html', reports=reports, pagination=pagination, title="所有销售报告")
