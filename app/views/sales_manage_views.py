from datetime import datetime

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, url_for
)
from flask_login import current_user, login_required

from app.extensions import db
from app.forms.sales_check_forms import SalesCheckForm
from app.forms.sales_forms import SalesForm
from app.models import DailySales, Store, FinancialCheckStatus, RoleType, BankDepositHistory

sales_manage_bp = Blueprint('sales_manage', __name__)


# 营业信息管理列表
@sales_manage_bp.route('/manage/list', methods=['GET'])
@login_required
def manage_list():
    store_id = request.args.get('store_id', default='', type=str)
    date_str = request.args.get('report_date', default='', type=str)
    # 默认状态为待审核
    financial_check_status = request.args.get('financial_check_status', default='PENDING', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    role = getattr(current_user.role, 'value', None) if hasattr(current_user.role, 'value') else str(current_user.role)
    if role in ['BRANCH_MANAGER', 'EMPLOYEE']:
        if hasattr(current_user, 'store_id') and current_user.store_id:
            stores = Store.query.filter_by(store_id=current_user.store_id).all()
        else:
            stores = []
    else:
        stores = Store.query.order_by(Store.store_name).all()
    query = DailySales.query
    if store_id:
        query = query.filter(DailySales.store_id == store_id)
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(DailySales.report_date == date_obj)
        except Exception:
            pass
    if financial_check_status == 'PENDING':
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.PENDING)
    elif financial_check_status == 'APPROVED':
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.APPROVED)
    query = query.order_by(DailySales.report_date.desc(), DailySales.store_id)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('sales_manage/list.html',
                           pagination=pagination,
                           stores=stores,
                           store_id=store_id,
                           report_date=date_str,
                           financial_check_status=financial_check_status,
                           title="营业信息管理"
                           )


# 日报详情
@sales_manage_bp.route('/manage/detail/<int:report_id>', methods=['GET'])
@login_required
def detail(report_id):
    daily_sales = DailySales.query.get_or_404(report_id)
    history_list = BankDepositHistory.query.filter_by(report_id=report_id).order_by(
        BankDepositHistory.created_at.desc()).all()
    return render_template('sales_manage/detail.html', report=daily_sales, history_list=history_list)


# 创建日报（上报）
@sales_manage_bp.route('/manage/create', methods=['GET', 'POST'])
@login_required
def create():
    form = SalesForm()
    if current_user.role in [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]:
        user_stores = Store.query.order_by(Store.store_name).all()
    elif hasattr(current_user, 'store_id') and current_user.store_id:
        user_stores = Store.query.filter_by(store_id=current_user.store_id).all()
    else:
        user_stores = []
        flash('您的账户未关联任何店铺，无法新建日报。', 'warning')
    form.store_id.choices = [(s.store_id, s.store_name) for s in user_stores]
    if len(user_stores) == 1 and not form.store_id.data:
        form.store_id.data = str(user_stores[0].store_id)
    show_takeaway = False
    if form.store_id.data:
        current_store_obj = Store.query.filter_by(store_id=form.store_id.data).first()
        if current_store_obj:
            show_takeaway = bool(getattr(current_store_obj, 'third_party_platform', False))
    if not show_takeaway and form.store_id.data:
        form.takeaway_amount.data = 0
    if form.validate_on_submit():
        exists = DailySales.query.filter_by(store_id=form.store_id.data, report_date=form.report_date.data).first()
        if exists:
            flash('该门店该日期的日报已存在，不可重复创建。', 'danger')
            return render_template('sales_manage/create.html', form=form, show_takeaway=show_takeaway)
        daily_sales = DailySales(
            user_id=current_user.user_id,
            store_id=form.store_id.data,
            report_date=form.report_date.data,
            cash_income=form.cash_income.data or 0,
            pos_income=form.pos_income.data or 0,
            voucher_amount=form.voucher_amount.data or 0,
            takeaway_amount=form.takeaway_amount.data if show_takeaway else 0,
            electronic_actual_arrival=form.electronic_actual_arrival.data or 0,
            bank_deposit=form.bank_deposit.data or 0,
            bank_fee=form.bank_fee.data or 0
        )
        daily_sales.auto_calculate()
        db.session.add(daily_sales)
        db.session.flush()
        import os
        from werkzeug.utils import secure_filename
        from app.models import DailySalesAttachments, AttachmentType
        static_dir = os.path.join(current_app.root_path, 'static')
        upload_dir = os.path.join(static_dir, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_map = {
            'sales_slip_image': AttachmentType.sales_slip,
            'bank_receipt_image': AttachmentType.bank_receipt,
            'takeaway_platform_receipt': AttachmentType.takeaway_screenshot,
            'electronic_actual_arrival_receipt': AttachmentType.electronic_actual_arrival_receipt
        }
        for field, atype in file_map.items():
            file = request.files.get(field)
            if file and file.filename:
                filename = secure_filename(f"{daily_sales.report_id}_{field}_{file.filename}")
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                rel_path = os.path.join('uploads', filename)
                attachment = DailySalesAttachments(
                    report_id=daily_sales.report_id,
                    file_path=rel_path.replace('\\', '/'),
                    attachment_type=atype
                )
                db.session.add(attachment)
        db.session.commit()
        flash('日报创建成功！', 'success')
        return redirect(url_for('sales_manage.manage_list'))
    return render_template('sales_manage/create.html', form=form, show_takeaway=show_takeaway)


# 日报审核/编辑
@sales_manage_bp.route('/manage/check/<int:report_id>', methods=['GET', 'POST'])
@login_required
def manage_check_edit(report_id):
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales_manage.manage_list'))
    daily_sales = DailySales.query.get_or_404(report_id)
    if daily_sales.financial_check_status == FinancialCheckStatus.APPROVED or daily_sales.financial_check_status == 2:
        history_list = BankDepositHistory.query.filter_by(report_id=report_id).order_by(
            BankDepositHistory.created_at.desc()).all()
        return render_template('sales_manage/detail.html', report=daily_sales, history_list=history_list)
    form = SalesCheckForm(obj=daily_sales)
    if request.method == 'GET' and daily_sales.financial_check_status:
        form.financial_check_status.data = daily_sales.financial_check_status.value
    history_list = BankDepositHistory.query.filter_by(report_id=report_id).order_by(
        BankDepositHistory.created_at.desc()).all()
    editable_fields = [
        'cash_income', 'pos_income', 'voucher_amount',
        'electronic_actual_arrival', 'bank_deposit', 'bank_fee'
    ]
    if daily_sales.store and getattr(daily_sales.store, 'third_party_platform', False):
        editable_fields.append('takeaway_amount')
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
                reason = request.form.get(f'remark_{field}', '')
                if not reason:
                    flash(f'请填写“{field}”的变更理由', 'danger')
                    return render_template('sales_manage/check_edit.html', form=form, daily_sales=daily_sales,
                                           title='营业信息审核', history_list=history_list)
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
        try:
            daily_sales.financial_check_status = FinancialCheckStatus(form.financial_check_status.data)
        except Exception as e:
            current_app.logger.error(f"[审核保存] FinancialCheckStatus赋值异常: {e}")
            flash(f"审核状态赋值失败: {e}", 'danger')
            return render_template('sales_manage/check_edit.html', form=form, daily_sales=daily_sales,
                                   title='营业信息审核', history_list=history_list)
        daily_sales.remark = form.remark.data
        if changed:
            daily_sales.auto_calculate()
        db.session.commit()
        if changed:
            flash('关键字段已修改并记录历史：' + '; '.join(change_logs), 'success')
        else:
            flash('审核信息已保存', 'success')
        return redirect(url_for('sales_manage.manage_list', initial_load='true'))
    for att in getattr(daily_sales, 'attachments', []):
        if att.file_path and not att.file_path.startswith('uploads/'):
            att.file_path = 'uploads/' + att.file_path.split('uploads/')[-1]
    return render_template('sales_manage/check_edit.html', form=form, daily_sales=daily_sales, title='营业信息审核',
                           history_list=history_list)


# 审核列表（仅财务/管理员）
@sales_manage_bp.route('/manage/audit/list', methods=['GET'])
@login_required
def manage_audit_list():
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales_manage.manage_list'))
    store_id = request.args.get('store_id', default='', type=str)
    date_str = request.args.get('report_date', default='', type=str)
    financial_check_status = request.args.get('financial_check_status', default='PENDING', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    stores = Store.query.order_by(Store.store_name).all()
    query = DailySales.query
    if store_id:
        query = query.filter(DailySales.store_id == store_id)
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(DailySales.report_date == date_obj)
        except Exception:
            pass
    if financial_check_status == 'PENDING':
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.PENDING)
    elif financial_check_status == 'APPROVED':
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.APPROVED)
    query = query.order_by(DailySales.report_date.desc(), DailySales.store_id)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('sales_manage/list.html',
                           pagination=pagination,
                           stores=stores,
                           store_id=store_id,
                           report_date=date_str,
                           financial_check_status=financial_check_status,
                           title="销售核对"
                           )


# 日报上报列表（门店组/管理组）
@sales_manage_bp.route('/manage/report/list', methods=['GET'])
@login_required
def manage_report_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    role = getattr(current_user.role, 'value', None) if hasattr(current_user.role, 'value') else str(current_user.role)
    if role in ['branch_manager', 'employee', 'BRANCH_MANAGER', 'EMPLOYEE']:
        query = DailySales.query.filter_by(store_id=current_user.store_id).order_by(DailySales.created_at.desc())
    else:
        query = DailySales.query.order_by(DailySales.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    reports = pagination.items
    return render_template('sales_manage/list.html', reports=reports, pagination=pagination, title="营业日报列表")


# 日报上报创建（门店组/管理组）
@sales_manage_bp.route('/manage/report/create', methods=['GET', 'POST'])
@login_required
def manage_report_create():
    form = SalesForm()
    if current_user.role in [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]:
        user_stores = Store.query.order_by(Store.store_name).all()
    elif hasattr(current_user, 'store_id') and current_user.store_id:
        user_stores = Store.query.filter_by(store_id=current_user.store_id).all()
    else:
        user_stores = []
        flash('您的账户未关联任何店铺，无法新建日报。', 'warning')
    form.store_id.choices = [(s.store_id, s.store_name) for s in user_stores]
    if len(user_stores) == 1 and not form.store_id.data:
        form.store_id.data = str(user_stores[0].store_id)
    show_takeaway = False
    if form.store_id.data:
        current_store_obj = Store.query.filter_by(store_id=form.store_id.data).first()
        if current_store_obj:
            show_takeaway = bool(getattr(current_store_obj, 'third_party_platform', False))
    if not show_takeaway and form.store_id.data:
        form.takeaway_amount.data = 0
    if form.validate_on_submit():
        required_files = [
            ('sales_slip_image', 'POS机营业信息凭证'),
            ('bank_receipt_image', '银行存款凭证'),
            ('electronic_actual_arrival_receipt', '电子支付入账凭证')
        ]
        if show_takeaway:
            required_files.append(('takeaway_platform_receipt', '第三方外卖平台收入凭证'))
        missing = []
        for field, label in required_files:
            file = request.files.get(field)
            if not file or file.filename == '':
                missing.append(label)
        if missing:
            flash('请上传以下必需附件：' + '、'.join(missing), 'danger')
            return render_template('sales_manage/create.html', form=form, show_takeaway=show_takeaway)
        exists = DailySales.query.filter_by(store_id=form.store_id.data, report_date=form.report_date.data).first()
        if exists:
            flash('该门店该日期的日报已存在，不可重复创建。', 'danger')
            return render_template('sales_manage/create.html', form=form, show_takeaway=show_takeaway)
        daily_sales = DailySales(
            user_id=current_user.user_id,
            store_id=form.store_id.data,
            report_date=form.report_date.data,
            cash_income=form.cash_income.data or 0,
            pos_income=form.pos_income.data or 0,
            voucher_amount=form.voucher_amount.data or 0,
            takeaway_amount=form.takeaway_amount.data if show_takeaway else 0,
            electronic_actual_arrival=form.electronic_actual_arrival.data or 0,
            bank_deposit=form.bank_deposit.data or 0,
            bank_fee=form.bank_fee.data or 0
        )
        daily_sales.auto_calculate()
        daily_sales.pos_total = daily_sales.pos_total or 0
        daily_sales.total_error = daily_sales.total_error or 0
        daily_sales.actual_sales = daily_sales.actual_sales or 0
        db.session.add(daily_sales)
        db.session.flush()
        import os
        from werkzeug.utils import secure_filename
        from app.models import DailySalesAttachments, AttachmentType
        static_dir = os.path.join(current_app.root_path, 'static')
        upload_dir = os.path.join(static_dir, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_map = {
            'sales_slip_image': AttachmentType.sales_slip,
            'bank_receipt_image': AttachmentType.bank_receipt,
            'takeaway_platform_receipt': AttachmentType.takeaway_screenshot,
            'electronic_actual_arrival_receipt': AttachmentType.electronic_actual_arrival_receipt
        }
        for field, atype in file_map.items():
            file = request.files.get(field)
            if file and file.filename:
                filename = secure_filename(f"{daily_sales.report_id}_{field}_{file.filename}")
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                rel_path = os.path.join('uploads', filename)
                attachment = DailySalesAttachments(
                    report_id=daily_sales.report_id,
                    file_path=rel_path.replace('\\', '/'),
                    attachment_type=atype
                )
                db.session.add(attachment)
        db.session.commit()
        flash('日报创建成功！', 'success')
        return redirect(url_for('sales_manage.manage_report_list'))
    return render_template('sales_manage/create.html', form=form, show_takeaway=show_takeaway)
