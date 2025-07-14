from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, url_for, session
)
from flask_login import current_user, login_required
from app.extensions import db
from app.models import DailySales, RoleType, Store
from app.forms.sales_forms import SalesForm

sales_report_bp = Blueprint('sales_report', __name__)

@sales_report_bp.route('/report/list', methods=['GET'])
@login_required
def report_list():
    # 允许所有已登录用户访问日报列表
    page = request.args.get('page', 1, type=int)
    per_page = 20
    # 判断角色
    role = getattr(current_user.role, 'value', None) if hasattr(current_user.role, 'value') else str(current_user.role)
    if role in ['branch_manager', 'employee']:
        # 门店组：只看本店
        query = DailySales.query.filter_by(store_id=current_user.store_id).order_by(DailySales.created_at.desc())
    else:
        # 管理组：看全部
        query = DailySales.query.order_by(DailySales.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    reports = pagination.items
    return render_template('sales/report_list.html', reports=reports, pagination=pagination)

@sales_report_bp.route('/report/create', methods=['GET', 'POST'])
@login_required
def report_create():
    form = SalesForm()
    if current_user.role in [RoleType.ADMIN, RoleType.FINANCE, RoleType.HEAD_MANAGER]:
        user_stores = Store.query.order_by(Store.store_name).all()
    elif current_user.store_id:
        user_stores = Store.query.filter_by(store_id=current_user.store_id).all()
    else:
        user_stores = []
        flash('您的账户未关联任何店铺，无法新建日报。', 'warning')

    form.store_id.choices = [(s.store_id, s.store_name) for s in user_stores]
    # 只为单门店用户自动赋值
    if len(user_stores) == 1 and not form.store_id.data:
        form.store_id.data = str(user_stores[0].store_id)

    show_takeaway = False
    current_store = None
    if form.store_id.data:
        current_store_obj = Store.query.filter_by(store_id=form.store_id.data).first()
        if current_store_obj:
            current_store = current_store_obj.to_dict()
            show_takeaway = bool(current_store.get('third_party_platform', False))
    # 调试输出
    print('form.store_id.data:', form.store_id.data)
    print('current_store:', current_store)
    print('show_takeaway:', show_takeaway)
    if not show_takeaway and form.store_id.data:
        form.takeaway_amount.data = 0

    if form.validate_on_submit():
        # 附件必填校验
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
            return render_template('sales/report_create.html', form=form, show_takeaway=show_takeaway)

        exists = DailySales.query.filter_by(store_id=form.store_id.data, report_date=form.report_date.data).first()
        if exists:
            flash('该门店该日期的日报已存在，不可重复创建。', 'danger')
            return render_template('sales/report_create.html', form=form, show_takeaway=show_takeaway)
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
        db.session.flush()  # 获取ID

        # 附件保存
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
                # 只保存 uploads/xxx.jpg
                rel_path = os.path.join('uploads', filename)
                attachment = DailySalesAttachments(
                    report_id=daily_sales.report_id,
                    file_path=rel_path.replace('\\', '/'),
                    attachment_type=atype
                )
                db.session.add(attachment)

        db.session.commit()
        flash('日报创建成功！', 'success')
        return redirect(url_for('sales_report.report_list'))
    return render_template('sales/report_create.html', form=form, show_takeaway=show_takeaway)
