
# 销售核对审核处理（POST）
from app.forms.sales_check_forms import SalesCheckForm

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
from app.extensions import db
from app.models import DailySales, FinancialCheckStatus, RoleType, Store
sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/check/<int:report_id>', methods=['GET', 'POST'])
@login_required
def sales_check_edit(report_id):
    # 仅限财务/管理员
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales.sales_check_list'))

    daily_sales = DailySales.query.get_or_404(report_id)
    form = SalesCheckForm(obj=daily_sales)
    if form.validate_on_submit():
        daily_sales.bank_deposit = form.bank_deposit.data
        daily_sales.financial_check_status = form.financial_check_status.data
        daily_sales.remark = form.remark.data
        # 自动归档：审核通过即归档
        if daily_sales.financial_check_status == FinancialCheckStatus.APPROVED:
            daily_sales.archived = True
        db.session.commit()
        flash('审核信息已保存', 'success')
        return redirect(url_for('sales.sales_check_list', store_id=daily_sales.store_id, report_date=daily_sales.report_date.strftime('%Y-%m-%d')))
    # GET: 预填充表单
    return render_template('sales/check_edit.html', form=form, daily_sales=daily_sales, title='销售审核')
# 销售核对视图：管理员/财务可按门店编号、日期筛选，默认当天全部门店
@sales_bp.route('/list', methods=['GET'])
@login_required
def sales_check_list():
    # 仅限管理员/财务
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales.report_sales'))

    # 获取筛选参数
    store_id = request.args.get('store_id', type=str)
    date_str = request.args.get('report_date', datetime.today().strftime('%Y-%m-%d'))
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 门店列表（下拉用）
    stores = Store.query.order_by(Store.store_name).all()

    # 构建查询
    query = DailySales.query.filter_by(archived=False)
    if store_id:
        query = query.filter(DailySales.store_id == store_id)
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(DailySales.report_date == date_obj)
        except Exception:
            pass
    query = query.order_by(DailySales.report_date.desc(), DailySales.store_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('sales/list.html',
        pagination=pagination,
        stores=stores,
        store_id=store_id,
        report_date=date_str,
        title="销售核对"
    )
# app/views/sales_views.py
# 修订内容：1. 上传文件保存路径调整为 static/uploads；2. 自动创建 static/uploads 目录；3. 增加中文注释说明
from datetime import datetime
import os
import traceback
import pprint

from app.extensions import db
from app.forms.sales_forms import SalesForm
from app.models import DailySales, FinancialCheckStatus, RoleType, Store, User
from app.models.attachment import DailySalesAttachments
from app.models.enums import AttachmentType
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
from werkzeug.utils import secure_filename
from wtforms.validators import DataRequired, Optional



# Helper function for file uploads
# 修订：上传文件保存到 static/uploads，并自动创建该目录
# ---------------------------------------------
def save_attachment(form_field, report_id, attachment_type):
    """
    辅助函数：保存上传的文件并创建 DailySalesAttachments 记录。
    本次修订：
    1. 上传文件保存到 static/uploads 目录下
    2. 若 static/uploads 不存在则自动创建
    3. 数据库存储相对路径，便于前端展示

    支持多文件上传：form_field.data 可能为 FileStorage 或 list[FileStorage]
    """
    files = form_field.data
    if not files:
        return
    if not isinstance(files, list):
        files = [files]
    upload_folder = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    for file in files:
        if file and hasattr(file, 'filename') and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(upload_folder, filename)
            file.save(save_path)
            relative_path = os.path.join('uploads', filename)
            attachment = DailySalesAttachments(
                report_id=report_id,
                file_path=relative_path,
                attachment_type=attachment_type
            )
            db.session.add(attachment)


def apply_dynamic_validation(form, step):
    """Applies DataRequired validators based on the step.
    根据步骤应用 DataRequired 验证器。
    """
    required_fields = {
        'pos': ['store_id', 'report_date', 'cash_sales', 'electronic_sales', 'system_takeaway_sales', 'sales_slip_image'],
        'takeaway': ['store_id', 'report_date', 'takeaway_platform_sales', 'takeaway_platform_receipt'],
        'bank': ['store_id', 'report_date', 'electronic_actual_arrival', 'electronic_actual_arrival_receipt', 'bank_deposit', 'bank_fee', 'bank_receipt_image']
    }.get(step, [])  # Default to empty list if step is invalid

    for field_name, field in form._fields.items():
        # Remove DataRequired validator first
        field.validators = [v for v in field.validators if not isinstance(v, DataRequired)]
        # Add DataRequired if the field is required for the current step
        if field_name in required_fields:
            field.validators.insert(0, DataRequired())


@sales_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_sales():
    """Handles GET and POST requests for sales report submissions.
    处理营业额上报的 GET 和 POST 请求。
    """
    form = SalesForm()
    step = request.form.get('step')

    apply_dynamic_validation(form, step)

    # --- NEW: More concise equivalent of code above ---
    if current_user.role in [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]:
        user_stores = Store.query.order_by(Store.store_name).all()
    elif current_user.store_id:
        user_stores = Store.query.filter_by(store_id=current_user.store_id).all()
    else:
        user_stores = []
        flash('您的账户未关联任何店铺，无法上报数据，请联系管理员。', 'warning')
        current_app.logger.warning(f"门店组用户 {current_user.username} (ID: {current_user.user_id}) 未关联店铺。")

    form.store_id.choices = [(s.store_id, s.store_name) for s in user_stores]

    if current_app.config.get('ENV') == 'development':
        current_app.logger.info(f"当前数据库 URI: {current_app.config.get('SQLALCHEMY_DATABASE_URI')}")

    # 查询现有的日报
    daily_sales = None  # 初始化 daily_sales

    if form.validate_on_submit():
        try:
            # 【调试关键】 记录表单提交的数据
            current_app.logger.info(f"表单提交数据: {form.data}")
            # 【调试关键】 记录表单中的日期对象
            current_app.logger.info(f"表单中的日期对象: {form.report_date.data}")

            daily_sales = DailySales.query.filter_by(
                store_id=form.store_id.data,
                report_date=form.report_date.data,
                archived=False
            ).first()

            if daily_sales is None:
                # 【调试关键】 记录即将保存到数据库的日期
                current_app.logger.info(f"即将保存到数据库的日期: {form.report_date.data}")
                daily_sales = DailySales(
                    user_id=current_user.user_id,
                    store_id=form.store_id.data,
                    # 【调试关键】从表单获取日期
                    report_date=form.report_date.data
                )
                db.session.add(daily_sales)
                db.session.flush()
                flash('新的日报已创建，数据已保存！', 'success')
            else:
                flash('日报数据更新成功！', 'success')

            if step == 'pos':
                # POS机信息
                daily_sales.cash_income = float(form.cash_sales.data) if form.cash_sales.data is not None else 0.0
                daily_sales.pos_income = float(form.electronic_sales.data) if form.electronic_sales.data is not None else 0.0
                daily_sales.day_pass_income = float(form.system_takeaway_sales.data) if form.system_takeaway_sales.data is not None else 0.0
                daily_sales.voucher_amount = float(form.voucher_amount.data) if form.voucher_amount.data is not None else 0.0
                daily_sales.cash_difference = float(form.cash_difference.data) if form.cash_difference.data is not None else 0.0
                daily_sales.electronic_difference = float(form.electronic_difference.data) if form.electronic_difference.data is not None else 0.0
                # POS机净收入T = 现金 + 电子支付 + POS外卖 + 代金券
                daily_sales.pos_total = (daily_sales.cash_income or 0) + (daily_sales.pos_income or 0) + (daily_sales.day_pass_income or 0) + (daily_sales.voucher_amount or 0)
                # 多文件保存：支持所有相关字段
                for field, atype in [
                    ('sales_slip_image', AttachmentType.sales_slip),
                ]:
                    files = request.files.getlist(field)
                    for file in files:
                        if file and file.filename:
                            save_attachment(type('F', (), {'data': file})(), daily_sales.report_id, atype)
                # 步骤完成
                daily_sales.pos_info_completed = True
            elif step == 'takeaway':
                daily_sales.takeaway_amount = float(form.takeaway_platform_sales.data) if form.takeaway_platform_sales.data is not None else 0.0
                # 多文件保存 takeaway_screenshot
                for field, atype in [
                    ('takeaway_platform_receipt', AttachmentType.takeaway_screenshot),
                ]:
                    files = request.files.getlist(field)
                    for file in files:
                        if file and file.filename:
                            save_attachment(type('F', (), {'data': file})(), daily_sales.report_id, atype)
                daily_sales.takeaway_info_completed = True
            elif step == 'bank':
                # 电子支付实际入账金额及凭证（由用户填写）
                daily_sales.electronic_actual_arrival = float(form.electronic_actual_arrival.data) if form.electronic_actual_arrival.data is not None else 0.0
                for field, atype in [
                    ('electronic_actual_arrival_receipt', AttachmentType.electronic_actual_arrival_receipt),
                ]:
                    files = request.files.getlist(field)
                    for file in files:
                        if file and file.filename:
                            save_attachment(type('F', (), {'data': file})(), daily_sales.report_id, atype)
                # 银行存款及凭证
                daily_sales.bank_deposit = float(form.bank_deposit.data) if form.bank_deposit.data is not None else 0.0
                daily_sales.bank_fee = float(form.bank_fee.data) if form.bank_fee.data is not None else 0.0
                for field, atype in [
                    ('bank_receipt_image', AttachmentType.bank_receipt),
                ]:
                    files = request.files.getlist(field)
                    for file in files:
                        if file and file.filename:
                            save_attachment(type('F', (), {'data': file})(), daily_sales.report_id, atype)
                # 步骤完成条件：电子支付实际入账和银行存款都已填写且大于0
                if (daily_sales.electronic_actual_arrival is not None and daily_sales.electronic_actual_arrival > 0) \
                   and (daily_sales.bank_deposit is not None and daily_sales.bank_deposit > 0):
                    daily_sales.actual_arrival_info_completed = True

            elif request.form.get('submit_final') == 'final_submit':
                if daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed:
                    # --- 按模型注释公式自动计算相关字段 ---
                    # 店铺理论营业额 (T0) = 现金收入 + 电子支付收入 + 外卖收入 + 代金券使用金额
                    daily_sales.pos_total = (daily_sales.cash_income or 0) + (daily_sales.pos_income or 0) + (daily_sales.day_pass_income or 0) + (daily_sales.voucher_amount or 0)
                    # 实际总营业额(S)=第三方外卖平台收入(T1)+外卖收入+电子支付实际入账金额+银行存款金额
                    daily_sales.actual_sales = (daily_sales.takeaway_amount or 0) + (daily_sales.day_pass_income or 0) + (daily_sales.electronic_actual_arrival or 0) + (daily_sales.bank_deposit or 0)
                    # 总误差(E)=电子支付实际入账金额+银行存款金额+银行存款手续费-POS机小票里显示的电子支付总金额-POS机小票里显示的现金总金额
                    daily_sales.total_error = (daily_sales.electronic_actual_arrival or 0) + (daily_sales.bank_deposit or 0) + (daily_sales.bank_fee or 0) - (daily_sales.pos_income or 0) - (daily_sales.cash_income or 0)
                    daily_sales.is_submitted = True
                    flash('所有信息已最终提交，等待财务审核。', 'success')
                else:
                    flash('请先完成所有步骤再进行最终提交。', 'danger')
                    return redirect(url_for('sales.report_sales', report_date=daily_sales.report_date.strftime('%Y-%m-%d'), store_id=daily_sales.store_id))

            db.session.commit()
            current_app.logger.info(f"日报保存后主要字段: store_id={daily_sales.store_id}, report_date={daily_sales.report_date}, pos_info_completed={daily_sales.pos_info_completed}, takeaway_info_completed={daily_sales.takeaway_info_completed}, actual_arrival_info_completed={getattr(daily_sales, 'actual_arrival_info_completed', None)}, is_submitted={daily_sales.is_submitted}")
            return redirect(url_for('sales.report_sales', report_date=daily_sales.report_date.strftime('%Y-%m-%d'), store_id=daily_sales.store_id))

        except Exception as e:
            db.session.rollback()

            def safe_val(val):
                if isinstance(val, (int, float, str, type(None))):
                    return val
                if hasattr(val, 'filename'):
                    return f"<FileStorage: {getattr(val, 'filename', str(val))}>"
                try:
                    return str(val)
                except Exception:
                    return repr(val)

            safe_form_data = {k: safe_val(v) for k, v in form.data.items()}
            current_app.logger.error(
                f"保存销售日报时发生错误: {e} ({type(e)})\n"
                f"Traceback: {traceback.format_exc()}\n"
                f"用户: {getattr(current_user, 'username', None)} (ID: {getattr(current_user, 'user_id', None)})\n"
                f"表单数据: {pprint.pformat(safe_form_data)}\n"
                f"请求参数: {dict(request.form) if request.method == 'POST' else dict(request.args)}\n"
                f"请求路径: {request.path} [{request.method}]"
            )
            flash('保存日报时发生未知错误，请联系管理员。', 'danger')

    else:
        if form.errors:
            current_app.logger.warning(
                f"表单校验未通过: {form.errors}\n表单数据: {form.data}\n请求参数: {dict(request.form) if request.method == 'POST' else dict(request.args)}\n请求路径: {request.path} [{request.method}]"
            )

    # 【关键修改】只在首次加载页面时从 URL 获取参数
    initial_load = request.args.get('initial_load', False) == 'true' # 获取 initial_load 参数
    if request.method == 'GET' and not form.is_submitted() and initial_load: # 判断是否为首次加载
        selected_store_id = request.args.get('store_id', user_stores[0].store_id if user_stores else None)
        selected_date_str = request.args.get('report_date', datetime.today().strftime('%Y-%m-%d'))

         # 【调试关键】 记录预填充之前的 selected_date_str 和 form.report_date.data
        current_app.logger.info(f"预填充之前的 selected_date_str: {selected_date_str}")
        current_app.logger.info(f"预填充之前的 form.report_date.data: {form.report_date.data}")

        if selected_store_id:
            form.store_id.data = selected_store_id
        if selected_date_str:
            try:
                selected_date_str = selected_date_str.replace('/', '-')  # Standardize separator
                if '-' in selected_date_str:
                    form.report_date.data = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                elif len(selected_date_str) == 8:
                    form.report_date.data = datetime.strptime(selected_date_str, '%Y%m%d').date()
            except Exception:
                form.report_date.data = datetime.today().date()
         # 【调试关键】 记录预填充之后的 form.report_date.data
        current_app.logger.info(f"预填充之后的 form.report_date.data: {form.report_date.data}")

        # 【修正】预填充后立即查找日报，确保页面能加载到日报数据
        if form.store_id.data and form.report_date.data:
            daily_sales = DailySales.query.filter_by(
                store_id=form.store_id.data,
                report_date=form.report_date.data,
                archived=False
            ).first()
            if daily_sales:
                # 只在GET时赋值，POST时不覆盖
                form.cash_sales.data = daily_sales.cash_income
                form.electronic_sales.data = daily_sales.pos_income
                form.system_takeaway_sales.data = daily_sales.day_pass_income
                form.voucher_amount.data = daily_sales.voucher_amount
                form.cash_difference.data = daily_sales.cash_difference
                form.electronic_difference.data = daily_sales.electronic_difference
                form.sales_slip_image.data = None  # 文件字段不自动填充
                form.takeaway_platform_sales.data = daily_sales.takeaway_amount
                form.bank_deposit.data = daily_sales.bank_deposit
                form.bank_fee.data = daily_sales.bank_fee
                # 其它分步字段可按需补充

    return render_template('sales/report.html', form=form, title="上报营业额", daily_sales=daily_sales)