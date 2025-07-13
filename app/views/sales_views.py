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
from app.models import DailySales, FinancialCheckStatus, RoleType, Store, BankDepositHistory
sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/check/<int:report_id>', methods=['GET', 'POST'])
@login_required
def sales_check_edit(report_id):
    # 仅限财务/管理员
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales.sales_check_list'))

    daily_sales = DailySales.query.get_or_404(report_id)
    # 已审核则跳转到只读详情页
    if daily_sales.financial_check_status == FinancialCheckStatus.APPROVED or daily_sales.financial_check_status == 2:
        history_list = BankDepositHistory.query.filter_by(report_id=report_id).order_by(BankDepositHistory.created_at.desc()).all()
        return render_template('sales/report_detail.html', report=daily_sales, history_list=history_list)

    form = SalesCheckForm(obj=daily_sales)
    # 只在GET请求时赋值，避免POST时覆盖用户提交的值
    if request.method == 'GET' and daily_sales.financial_check_status:
        form.financial_check_status.data = daily_sales.financial_check_status.value
    history_list = BankDepositHistory.query.filter_by(report_id=report_id).order_by(BankDepositHistory.created_at.desc()).all()

    editable_fields = [
        'cash_income', 'pos_income', 'takeaway_amount',
        'electronic_actual_arrival', 'bank_deposit', 'bank_fee'
    ]

    if form.validate_on_submit():
        changed = False
        change_logs = []
        for field in editable_fields:
            old_value = getattr(daily_sales, field, None)
            new_value = request.form.get(field, None)
            try:
                new_value = float(new_value) if new_value is not None and new_value != '' else None
            except Exception:
                new_value = None
            if old_value != new_value and new_value is not None:
                reason = request.form.get(f'remark_{field}', '') or form.remark.data or ''
                if not reason:
                    flash(f'请填写“{field}”的变更理由', 'danger')
                    return render_template('sales/check_edit.html', form=form, daily_sales=daily_sales, title='营业信息审核', history_list=history_list)
                history = BankDepositHistory(
                    report_id=report_id,
                    field_name=field,
                    old_value=old_value,
                    new_value=new_value,
                    operator_id=current_user.user_id,
                    operator_role=getattr(current_user.role, 'value', ''),
                    remark=reason
                )
                db.session.add(history)
                setattr(daily_sales, field, new_value)
                changed = True
                change_logs.append(f'{field}: {old_value} → {new_value}，理由：{reason}')

        # 日志：表单提交的审核状态
        current_app.logger.warning(f"[审核保存] form.financial_check_status.data={form.financial_check_status.data} 类型={type(form.financial_check_status.data)}")
        current_app.logger.warning(f"[审核保存] 保存前 daily_sales.financial_check_status={daily_sales.financial_check_status} 类型={type(daily_sales.financial_check_status)}")
        # 修正：将表单值转换为FinancialCheckStatus枚举类型
        try:
            daily_sales.financial_check_status = FinancialCheckStatus(form.financial_check_status.data)
        except Exception as e:
            current_app.logger.error(f"[审核保存] FinancialCheckStatus赋值异常: {e}")
            flash(f"审核状态赋值失败: {e}", 'danger')
            return render_template('sales/check_edit.html', form=form, daily_sales=daily_sales, title='营业信息审核', history_list=history_list)
        daily_sales.remark = form.remark.data
        current_app.logger.warning(f"[审核保存] 保存后 daily_sales.financial_check_status={daily_sales.financial_check_status} 类型={type(daily_sales.financial_check_status)}")
        # 审核通过不再归档，仅以审核状态标识业务流程
        pass
        if changed:
            daily_sales.auto_calculate()
        db.session.commit()
        current_app.logger.warning(f"[审核保存] 提交后数据库 daily_sales.financial_check_status={daily_sales.financial_check_status} 类型={type(daily_sales.financial_check_status)}")
        if changed:
            flash('关键字段已修改并记录历史：' + '; '.join(change_logs), 'success')
        else:
            flash('审核信息已保存', 'success')
        # 审核完成后返回列表页，带初始参数（全部门店、全部日期、待审核）
        return redirect(url_for('sales.sales_check_list', initial_load='true'))
    return render_template('sales/check_edit.html', form=form, daily_sales=daily_sales, title='营业信息审核', history_list=history_list)
# 销售核对视图：管理员/财务可按门店编号、日期筛选，默认当天全部门店
@sales_bp.route('/list', methods=['GET'])
@login_required
def sales_check_list():
    # 仅限管理员/财务
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales.report_sales'))

    # 获取筛选参数，第一次加载时默认：门店全部、日期全部、审核状态“待审核”
    store_id = request.args.get('store_id', default='', type=str)
    date_str = request.args.get('report_date', default='', type=str)
    financial_check_status = request.args.get('financial_check_status', default='PENDING', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 门店列表（下拉用）
    stores = Store.query.order_by(Store.store_name).all()

    # 构建查询（已移除archived逻辑，仅以审核状态区分）
    query = DailySales.query
    if store_id:
        query = query.filter(DailySales.store_id == store_id)
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(DailySales.report_date == date_obj)
        except Exception:
            pass
    # 默认只查待审核（PENDING），除非用户选择其它
    if financial_check_status == 'PENDING':
        from app.models.enums import FinancialCheckStatus
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.PENDING)
    elif financial_check_status == 'APPROVED':
        from app.models.enums import FinancialCheckStatus
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.APPROVED)
    # 否则全部
    query = query.order_by(DailySales.report_date.desc(), DailySales.store_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('sales/list.html',
        pagination=pagination,
        stores=stores,
        store_id=store_id,
        report_date=date_str,
        financial_check_status=financial_check_status,
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
from app.models import DailySales, FinancialCheckStatus, RoleType, Store, User, BankDepositHistory
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
from wtforms.validators import DataRequired, Optional, NumberRange



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
    """Apply validators dynamically based on the step.
    根据步骤动态应用验证器。
    """
    required_fields = {
        'pos': ['store_id', 'report_date', 'cash_sales', 'electronic_sales', 'system_takeaway_sales', 'sales_slip_image'],
        'takeaway': ['store_id', 'report_date', 'takeaway_platform_sales', 'takeaway_platform_receipt'],
        'bank': ['store_id', 'report_date', 'electronic_actual_arrival', 'electronic_actual_arrival_receipt', 'bank_deposit', 'bank_fee', 'bank_receipt_image']
    }.get(step, [])  # Default to empty list if step is invalid

    monetary_fields = ['cash_sales', 'electronic_sales', 'system_takeaway_sales', 'voucher_amount', 'takeaway_platform_sales', 'electronic_actual_arrival', 'bank_deposit', 'bank_fee']

    for field_name, field in form._fields.items():
        # 先移除所有 DataRequired
        field.validators = [v for v in field.validators if not isinstance(v, DataRequired)]
        # 只为非货币字段添加 DataRequired
        if field_name in required_fields and field_name not in monetary_fields:
            field.validators.insert(0, DataRequired())
        # 只为货币字段添加 Optional + NumberRange
        if field_name in monetary_fields:
            field.validators = [v for v in field.validators if not isinstance(v, (NumberRange, Optional))]
            field.validators.append(Optional())
            field.validators.append(NumberRange(min=0, max=1000000, message="金额必须在0到1,000,000之间"))


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
                report_date=form.report_date.data
            ).first()

            if daily_sales:
                # 预加载附件数据
                daily_sales.attachments.all()

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

            show_final_submit_hint = False
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
                # 获取当前店铺信息以判断是否需要外卖平台信息
                current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
                # 判断是否需要外卖平台信息
                need_takeaway = current_store and current_store.third_party_platform
                # 如果不需要外卖平台信息，则自动标记为完成
                if not need_takeaway:
                    daily_sales.takeaway_info_completed = True
                # 检查是否所有必要步骤都已完成
                if daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed and not daily_sales.is_submitted:
                    show_final_submit_hint = True
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
                # 获取当前店铺信息
                current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
                need_takeaway = current_store and current_store.third_party_platform
                # 检查是否所有必要步骤都已完成
                if daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed and not daily_sales.is_submitted:
                    show_final_submit_hint = True
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
                # 步骤完成条件：电子支付实际入账和银行存款都已填写（允许为0）
                if (form.electronic_actual_arrival.data is not None and form.bank_deposit.data is not None):
                    daily_sales.actual_arrival_info_completed = True
                # 获取当前店铺信息
                current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
                need_takeaway = current_store and current_store.third_party_platform
                # 如果不需要外卖平台信息，则确保标记为完成
                if not need_takeaway:
                    daily_sales.takeaway_info_completed = True
                # 检查是否所有必要步骤都已完成
                if daily_sales.pos_info_completed and daily_sales.takeaway_info_completed and daily_sales.actual_arrival_info_completed and not daily_sales.is_submitted:
                    show_final_submit_hint = True

            elif request.form.get('submit_final') == 'final_submit':
                # 获取当前店铺信息，判断是否需要外卖平台信息
                current_store = Store.query.filter_by(store_id=daily_sales.store_id).first()
                need_takeaway = current_store and current_store.third_party_platform
                
                # 如果不需要外卖平台信息，确保标记为完成
                if not need_takeaway:
                    daily_sales.takeaway_info_completed = True
                
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
            # 如果所有步骤都已完成但未最终提交，提示用户是否要最终提交
            if show_final_submit_hint:
                flash('所有步骤已完成，是否要最终提交？请点击下方“我已确认，最终提交所有信息”按钮。', 'info')
            # 无论是否 show_final_submit_hint，均重定向，保证页面变量刷新
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


    # 【修正】GET 请求时，如果有 store_id 和 report_date 参数，无论 initial_load 是否 true，都赋值给 form，保证 tab 能正常显示
    if request.method == 'GET' and not form.is_submitted():
        selected_store_id = request.args.get('store_id')
        selected_date_str = request.args.get('report_date')
        if not selected_store_id and user_stores:
            selected_store_id = user_stores[0].store_id
        if not selected_date_str:
            selected_date_str = datetime.today().strftime('%Y-%m-%d')

        if selected_store_id:
            form.store_id.data = selected_store_id
        if selected_date_str:
            try:
                selected_date_str = selected_date_str.replace('/', '-')
                if '-' in selected_date_str:
                    form.report_date.data = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                elif len(selected_date_str) == 8:
                    form.report_date.data = datetime.strptime(selected_date_str, '%Y%m%d').date()
            except Exception:
                form.report_date.data = datetime.today().date()

        # 预填充后立即查找日报，确保页面能加载到日报数据
        if form.store_id.data and form.report_date.data:
            daily_sales = DailySales.query.filter_by(
                store_id=form.store_id.data,
                report_date=form.report_date.data
            ).first()
            if daily_sales:
                daily_sales.attachments.all()
                form.cash_sales.data = daily_sales.cash_income
                form.electronic_sales.data = daily_sales.pos_income
                form.system_takeaway_sales.data = daily_sales.day_pass_income
                form.voucher_amount.data = daily_sales.voucher_amount
                form.cash_difference.data = daily_sales.cash_difference
                form.electronic_difference.data = daily_sales.electronic_difference
                form.sales_slip_image.data = None
                form.takeaway_platform_sales.data = daily_sales.takeaway_amount
                form.bank_deposit.data = daily_sales.bank_deposit
                form.bank_fee.data = daily_sales.bank_fee
                form.electronic_actual_arrival.data = daily_sales.electronic_actual_arrival

    # 获取当前选中店铺的信息，用于模板判断是否显示外卖平台Tab
    current_store = None
    if form.store_id.data:
        current_store = Store.query.filter_by(store_id=form.store_id.data).first()
    
    # 如果有daily_sales，确保附件数据被预加载
    if daily_sales:
        daily_sales.attachments.all()
    
    # 创建店铺字典，便于模板查找店铺信息
    stores_dict = {s.store_id: s for s in user_stores}
    
    return render_template('sales/report.html', form=form, title="上报营业额", daily_sales=daily_sales, current_store=current_store, stores_dict=stores_dict)