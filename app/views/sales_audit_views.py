"""
销售审核相关视图（审核、审核列表、审核详情等）
"""
from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, url_for
)
from flask_login import current_user, login_required
from app.extensions import db
from app.models import DailySales, FinancialCheckStatus, RoleType, Store, BankDepositHistory
from app.forms.sales_check_forms import SalesCheckForm
from datetime import datetime

sales_audit_bp = Blueprint('sales_audit', __name__)

@sales_audit_bp.route('/check/<int:report_id>', methods=['GET', 'POST'])
@login_required
def sales_check_edit(report_id):
    # 仅限财务/管理员
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales_audit.sales_check_list'))

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

    # 根据门店是否开通外卖平台，动态决定可编辑字段
    editable_fields = [
        'cash_income', 'pos_income',
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
        return redirect(url_for('sales_audit.sales_check_list', initial_load='true'))
    # 确保所有附件路径都为 uploads/xxx
    for att in getattr(daily_sales, 'attachments', []):
        if att.file_path and not att.file_path.startswith('uploads/'):
            # 只保留 uploads/xxx
            att.file_path = 'uploads/' + att.file_path.split('uploads/')[-1]
    return render_template('sales/check_edit.html', form=form, daily_sales=daily_sales, title='营业信息审核', history_list=history_list)

@sales_audit_bp.route('/list', methods=['GET'])
@login_required
def sales_check_list():
    # 仅限管理员/财务
    if current_user.role not in [RoleType.ADMIN, RoleType.FINANCE]:
        flash('无权访问该页面', 'danger')
        return redirect(url_for('sales_report.report_list'))

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
        query = query.filter(DailySales.financial_check_status == FinancialCheckStatus.PENDING)
    elif financial_check_status == 'APPROVED':
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
