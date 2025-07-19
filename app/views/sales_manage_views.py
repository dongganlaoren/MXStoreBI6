from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, url_for
)
from flask_login import current_user, login_required
from app.extensions import db
from app.models import DailySales, Store, FinancialCheckStatus, RoleType
from app.forms.sales_forms import SalesForm
from datetime import datetime, date

sales_manage_bp = Blueprint('sales_manage', __name__)

@sales_manage_bp.route('/manage/list', methods=['GET'])
@login_required
def manage_list():
    # 允许所有已登录用户访问
    store_id = request.args.get('store_id', default='', type=str)
    date_str = request.args.get('report_date', default='', type=str)
    financial_check_status = request.args.get('financial_check_status', default='', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # 根据角色过滤门店列表
    role = getattr(current_user.role, 'value', None) if hasattr(current_user.role, 'value') else str(current_user.role)
    if role in ['BRANCH_MANAGER', 'EMPLOYEE']:
        # 店铺组：只能看到自己门店
        if hasattr(current_user, 'store_id') and current_user.store_id:
            stores = Store.query.filter_by(store_id=current_user.store_id).all()
        else:
            stores = []
    else:
        # 管理组：可看全部门店
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

@sales_manage_bp.route('/manage/detail/<int:report_id>', methods=['GET'])
@login_required
def detail(report_id):
    from app.models import BankDepositHistory
    daily_sales = DailySales.query.get_or_404(report_id)
    history_list = BankDepositHistory.query.filter_by(report_id=report_id).order_by(BankDepositHistory.created_at.desc()).all()
    return render_template('sales_manage/detail.html', report=daily_sales, history_list=history_list)

@sales_manage_bp.route('/manage/create', methods=['GET', 'POST'])
@login_required
def create():
    form = SalesForm()
    # 门店权限与原有逻辑一致
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
    current_store = None
    if form.store_id.data:
        current_store_obj = Store.query.filter_by(store_id=form.store_id.data).first()
        if current_store_obj:
            current_store = current_store_obj.to_dict()
            show_takeaway = bool(current_store.get('third_party_platform', False))
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
        db.session.flush()  # 获取ID
        # 附件保存（与原有一致）
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
