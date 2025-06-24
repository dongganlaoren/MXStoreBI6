# app/views/sales_views.py

from datetime import datetime

from app.extensions import db
from app.forms.sales_forms import SalesForm

# 从 __init__.py 统一导入所有需要的模型和枚举，结构更清晰
from app.models import (
    DailySales,
    RoleType,
    Store,
    StoreStaff,
)

# 从我们之前创建的 helpers.py 中导入文件保存函数
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

# 创建一个名为 'sales' 的蓝图
sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    """
    统一处理营业信息上报的GET和POST请求。
    这是本模块唯一的、也是最核心的视图函数。
    """
    form = SalesForm()

    # --- 权限控制：根据用户角色动态获取其能操作的店铺列表 ---
    if current_user.role in [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]:
        user_stores = Store.query.all()
    else:
        # 对于店员或分店长，需要通过 store_staff 表找到他们关联的店铺
        staff_entry = StoreStaff.query.filter_by(user_id=current_user.user_id).first()
        if staff_entry:
            user_stores = Store.query.filter_by(store_id=staff_entry.store_id).all()
        else:
            user_stores = []
            flash('当前用户未关联任何店铺，请联系管理员。', 'warning')
            current_app.logger.warning(f"用户 {current_user.username} (ID: {current_user.user_id}) 未关联任何店铺。")

    # 将获取到的店铺列表填充到表单的下拉选项中
    form.store_id.choices = [(s.store_id, s.store_name) for s in user_stores]

    # --- POST 请求处理逻辑 ---
    # 我们先处理POST请求，因为如果表单提交且验证成功，会直接重定向，无需再执行GET的逻辑
    if form.validate_on_submit():
        # 根据提交按钮的 name 属性，来判断用户意图，并分发到不同的处理函数
        if 'submit_pos' in request.form:
            return handle_pos_submission(form)
        # 我们可以为其他按钮添加类似的处理逻辑
        # elif 'submit_takeaway' in request.form:
        #     return handle_takeaway_submission(form)
        # elif 'submit_bank' in request.form:
        #     return handle_bank_submission(form)
        # elif 'submit_final' in request.form:
        #     return handle_final_submission(form)

    # --- GET 请求处理逻辑 ---
    # 目的：当用户通过页面顶部的选择器选择一个店铺和日期时，加载数据库中已有的数据，并预填充到表单中

    # 尝试从URL参数中获取店铺ID和日期，如果没有则使用默认值
    selected_store_id = request.args.get('store_id', user_stores[0].store_id if user_stores else None)
    # 默认显示今天的日期
    selected_date_str = request.args.get('report_date', datetime.today().strftime('%Y-%m-%d'))

    # 将获取到的值预设到表单中，以便在页面上正确显示当前用户的选择
    form.store_id.data = selected_store_id
    form.report_date.data = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

    daily_sales = None
    if selected_store_id:
        # 查询数据库，看是否存在匹配的日报记录
        daily_sales = DailySales.query.filter_by(
            store_id=selected_store_id,
            report_date=form.report_date.data
        ).first()

    if daily_sales:
        # 如果找到了记录，用它的数据自动填充整个表单
        # WTForms 的 process(obj=...) 方法会智能地将模型对象的属性填充到同名的表单字段中
        form.process(obj=daily_sales)

    # 渲染页面，并将表单和可能存在的日报对象(daily_sales)传递给模板
    # 模板可以根据 daily_sales 是否存在及其状态，来决定显示哪些内容
    return render_template('sales/report.html', form=form, daily_sales=daily_sales)


def handle_pos_submission(form):
    """处理第一步：“POS机小票”上报逻辑"""
    store_id = form.store_id.data
    report_date = form.report_date.data

    # 查询或创建日报对象
    daily_sales = DailySales.query.filter_by(store_id=store_id, report_date=report_date).first()
    if not daily_sales:
        daily_sales = DailySales(store_id=store_id, report_date=report_date, user_id=current_user.user_id)
        db.session.add(daily_sales)
    elif daily_sales.is_submitted:
        flash('该日报已最终提交，无法修改。', 'warning')
        return redirect(url_for('sales.report', report_date=report_date.strftime('%Y-%m-%d'), store_id=store_id))

    # --- 数据对齐与更新 ---
    # 由于您的表单字段名（如 cash_sales）和模型字段名（如 cash_income）不完全一致，我们在这里进行手动匹配
    # 这是一个很好的例子，说明了保持命名一致性的重要性
    daily_sales.total_income = form.cash_sales.data + form.electronic_sales.data + form.system_takeaway_sales.data
    daily_sales.cash_income = form.cash_sales.data
    daily_sales.pos_income = form.electronic_sales.data
    daily_sales.day_pass_income = form.system_takeaway_sales.data
    daily_sales.voucher_amount = form.voucher_amount.data
    # 误差字段您的新模型中没有，我们暂时不处理

    # 更新状态
    daily_sales.pos_info_completed = True

    try:
        db.session.commit()
        # 记录成功的日志
        current_app.logger.info(f"用户 {current_user.username} 成功保存了店铺 {store_id} 在 {report_date} 的POS机信息。")
        flash('第一步：POS机数据及凭证上报成功!', 'success')
    except Exception as e:
        db.session.rollback()
        # 记录失败的日志
        current_app.logger.error(f"用户 {current_user.username} 保存POS机信息失败: {e}", exc_info=True)
        flash(f'发生未知错误，数据上报失败，请联系管理员。', 'danger')

    # 操作完成后，重定向回report页面，并带上当前操作的店铺和日期，以便页面刷新后保持上下文
    return redirect(url_for('sales.report', report_date=report_date.strftime('%Y-%m-%d'), store_id=store_id))

# 我们可以为后续的步骤也创建类似的 handle 函数
# def handle_takeaway_submission(form):
#     # ...
#
# def handle_bank_submission(form):
#     # ...
#
# def handle_final_submission(form):
#     # ...