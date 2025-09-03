import os
import smtplib
import ssl
from datetime import datetime, date, timedelta
from typing import Any, Optional, Tuple

from apscheduler.triggers.cron import CronTrigger
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, Response, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.models import User, DailySales, Store
from app.models.email_report_config import EmailReportConfig
from app.models.email_task_log import EmailTaskLog, EmailTaskType, EmailTaskStatus
from app.models.enums import ReimbursementStatus
from app.models.enums import RoleType, FinancialCheckStatus, ReimbursementPrimaryCategory, ReimbursementCheckStatus
from app.models.reimbursement import ReimbursementRequest
from app.utils.notify import send_notify_mail
from app.utils.notify import send_sales_report_mail, query_sales_reports, render_sales_report_html

# 定时任务注册入口
email_report_bp = Blueprint('email_report', __name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../email_report_config.json')


def register_email_report_tasks(scheduler, app):
    """
    注册销售报表邮件定时任务
    """
    # 日报任务
    scheduler.add_job(
        func=lambda: send_report_task('day', RoleType.BRANCH_MANAGER, app),
        trigger=CronTrigger(hour=20, minute=0),
        id='branch_manager_daily_report',
        replace_existing=True
    )
    scheduler.add_job(
        func=lambda: send_report_task('day', [RoleType.ADMIN, RoleType.HEAD_MANAGER, RoleType.FINANCE], app),
        trigger=CronTrigger(hour=16, minute=0),
        id='admin_finance_daily_report',
        replace_existing=True
    )
    # 周���������任务
    scheduler.add_job(
        func=lambda: send_report_task('week', RoleType.BRANCH_MANAGER, app),
        trigger=CronTrigger(day_of_week='mon', hour=10, minute=0),
        id='branch_manager_weekly_report',
        replace_existing=True
    )
    scheduler.add_job(
        func=lambda: send_report_task('week', [RoleType.ADMIN, RoleType.HEAD_MANAGER, RoleType.FINANCE], app),
        trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='admin_finance_weekly_report',
        replace_existing=True
    )
    # 月报任务
    scheduler.add_job(
        func=lambda: send_report_task('month', RoleType.BRANCH_MANAGER, app),
        trigger=CronTrigger(day=1, hour=10, minute=0),
        id='branch_manager_monthly_report',
        replace_existing=True
    )
    scheduler.add_job(
        func=lambda: send_report_task('month', [RoleType.ADMIN, RoleType.HEAD_MANAGER, RoleType.FINANCE], app),
        trigger=CronTrigger(day=1, hour=9, minute=0),
        id='admin_finance_monthly_report',
        replace_existing=True
    )


def send_report_task(period, roles, app):
    """
    定时发送销售报表任务（支持分角色、分批、错误重试、日志记录）
    """
    with app.app_context():
        app.logger.info(f"[邮��任务] 开始执行 send_report_task, period={period}, roles={roles}")
        if not isinstance(roles, list):
            roles = [roles]
        users = User.query.filter(User.role.in_(roles)).all()
        app.logger.info(f"[邮件任务] 目标用户数量: {len(users)}")
        batch_size = 100
        for i in range(0, len(users), batch_size):
            batch_users = users[i:i + batch_size]
            recipients = [u.email for u in batch_users if u.email]
            success_count = 0
            fail_count = 0
            status = EmailTaskStatus.success
            for u in batch_users:
                # 修复：User 主键为 user_id
                app.logger.info(f"[邮件任务] 正在发送: period={period}, user={u.user_id}, email={u.email}")
                ok = send_sales_report_mail(period, u.role, u, [u.email])
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            if fail_count > 0 and success_count > 0:
                status = EmailTaskStatus.partial_fail
            elif fail_count > 0 and success_count == 0:
                status = EmailTaskStatus.fail
            else:
                status = EmailTaskStatus.success
            # period -> EmailTaskType 键映射
            period_map = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}
            task_key = period_map.get(period, 'daily')
            log = EmailTaskLog(
                task_type=EmailTaskType[task_key],
                start_date=datetime.now().date(),
                end_date=datetime.now().date(),
                recipients=','.join(recipients),
                status=status,
                success_count=success_count,
                fail_count=fail_count
            )
            db.session.add(log)
            try:
                db.session.commit()
                app.logger.info(
                    f"[邮件任务] 日志已写入: log_id={log.id}, status={status}, success={success_count}, fail={fail_count}")
            except Exception as e:
                app.logger.error(f"[邮件任务] 日志写入失败: {e}")


@email_report_bp.route('/email_report/send_all', methods=['POST', 'GET'])
def send_all_reports():
    """
    手动触发：将所有类型报表发送到指定邮箱（测试入口）
    """
    target_email = request.args.get('email') or '32191681@qq.com'
    from app.models import User, RoleType
    # 取一个总部用户和一个分店长用户（如无则跳过）
    admin_user = User.query.filter(User.role == RoleType.ADMIN).first()
    branch_user = User.query.filter(User.role == RoleType.BRANCH_MANAGER).first()
    results = []
    # 日报
    if branch_user:
        ok = send_sales_report_mail('day', branch_user.role, branch_user, [target_email])
        results.append({'type': '分店长日报', 'success': ok})
    if admin_user:
        ok = send_sales_report_mail('day', admin_user.role, admin_user, [target_email])
        results.append({'type': '总部日报', 'success': ok})
    # 周报
    if branch_user:
        ok = send_sales_report_mail('week', branch_user.role, branch_user, [target_email])
        results.append({'type': '分店长周报', 'success': ok})
    if admin_user:
        ok = send_sales_report_mail('week', admin_user.role, admin_user, [target_email])
        results.append({'type': '总部周报', 'success': ok})
    # 月报
    if branch_user:
        ok = send_sales_report_mail('month', branch_user.role, branch_user, [target_email])
        results.append({'type': '分店长月报', 'success': ok})
    if admin_user:
        ok = send_sales_report_mail('month', admin_user.role, admin_user, [target_email])
        results.append({'type': '总部月报', 'success': ok})
    return jsonify({'email': target_email, 'results': results})


@email_report_bp.route('/email_report/config', methods=['GET', 'POST'])
def email_report_config():
    """
    销售汇总信息发送任务配置管理页面（数据库版）
    """
    from app.models.enums import RoleType
    # 默认角色列表
    role_list = ['ADMIN', 'HEAD_MANAGER', 'FINANCE', 'BRANCH_MANAGER']
    configs: dict[str, EmailReportConfig] = {}
    for r in role_list:
        cfg = EmailReportConfig.query.filter_by(role=RoleType[r]).first()
        if not cfg:
            cfg = EmailReportConfig(role=RoleType[r])
            if r == 'BRANCH_MANAGER':
                cfg.daily_time = '20:00'
                cfg.weekly_time = '10:00'
                cfg.monthly_time = '10:00'
            db.session.add(cfg)
            db.session.commit()
            cfg = EmailReportConfig.query.filter_by(role=RoleType[r]).first()
        # 保证放入的都是非空 EmailReportConfig
        if cfg is not None:
            configs[r] = cfg
    if request.method == 'POST':
        action = request.form.get('action', 'save')
        for r in role_list:
            cfg = configs[r]
            cfg.emails = request.form.get(f'{r}_emails', '')
            cfg.daily_enabled = bool(request.form.get(f'{r}_daily_enabled'))
            cfg.weekly_enabled = bool(request.form.get(f'{r}_weekly_enabled'))
            cfg.monthly_enabled = bool(request.form.get(f'{r}_monthly_enabled'))
            cfg.daily_time = request.form.get(f'{r}_daily_time', cfg.daily_time)
            cfg.weekly_time = request.form.get(f'{r}_weekly_time', cfg.weekly_time)
            cfg.monthly_time = request.form.get(f'{r}_monthly_time', cfg.monthly_time)
            cfg.weekly_day = request.form.get(f'{r}_weekly_day', cfg.weekly_day)
            cfg.monthly_day = request.form.get(f'{r}_monthly_day', cfg.monthly_day)
            db.session.commit()
        if action == 'send':
            from app.utils.notify import send_sales_report_mail
            from app.models import User, EmailTaskLog, EmailTaskType, EmailTaskStatus
            send_count = 0
            success_count = 0
            fail_count = 0
            recipients = []
            for r in role_list:
                users = User.query.filter(User.role == RoleType[r]).all()
                for u in users:
                    for period in ['day', 'week', 'month']:
                        ok = send_sales_report_mail(period, u.role, u, [u.email])
                        recipients.append(u.email)
                        send_count += 1
                        if ok:
                            success_count += 1
                        else:
                            fail_count += 1
            status = EmailTaskStatus.success
            if fail_count > 0 and success_count > 0:
                status = EmailTaskStatus.partial_fail
            elif fail_count > 0 and success_count == 0:
                status = EmailTaskStatus.fail
            else:
                status = EmailTaskStatus.success
            # 日志写入（只记录一次，类型为manual）
            valid_recipients = [r for r in recipients if r]
            log = EmailTaskLog(
                task_type=EmailTaskType.daily,  # 可选：可用'daily'或'manual'，此处用'daily'保持一致
                start_date=datetime.now().date(),
                end_date=datetime.now().date(),
                recipients=','.join(valid_recipients),
                status=status,
                success_count=success_count,
                fail_count=fail_count
            )
            db.session.add(log)
            db.session.commit()
            flash(f'已手动触发发送 {send_count} 封邮件（每角色日报/周报/月报各一次）', 'success')
            return redirect(url_for('email_report.email_report_config'))
        else:
            flash('配置已保存', 'success')
            return redirect(url_for('email_report.email_report_config'))
    # 构造 config 数据结构供模板使用
    roles_dict = {r: cfg.to_dict() for r, cfg in configs.items()}
    config: dict[str, Any] = {'roles': roles_dict}
    # 构造发送频率及统计周期说明
    freq_desc = []
    for r, info in configs.items():
        role_name = r
        # 日报
        if info.daily_enabled:
            freq_desc.append(
                f"<span style='color:#5470C6;font-weight:600;'>{role_name}日报：</span>每天{info.daily_time}发送，统计前���天数据。")
        # 周报
        if info.weekly_enabled:
            week_map = ['一', '二', '三', '四', '五', '六', '日']
            week_day = int(info.weekly_day) if str(info.weekly_day).isdigit() else 1
            freq_desc.append(
                f"<span style='color:#5470C6;font-weight:600;'>{role_name}周报：</span>每周{week_map[week_day - 1]} {info.weekly_time}发送，统计上一周数据。")
        # 月报
        if info.monthly_enabled:
            freq_desc.append(
                f"<span style='color:#5470C6;font-weight:600;'>{role_name}月报：</span>每月{info.monthly_day}日 {info.monthly_time}发送，统计上个月数据。")
    freq_desc.append("<span style='color:#d43f3a;'>收件人自动从用户表提取，无需配置。</span>")
    config['freq_desc'] = freq_desc
    return render_template('email_report/config_form.html', config=config)


@email_report_bp.route('/email_report/log_list', methods=['GET'])
def email_report_log_list():
    """
    邮件发送任务执行日志页面
    """
    logs = EmailTaskLog.query.order_by(EmailTaskLog.created_at.desc()).limit(200).all()
    return render_template('email_report/log_list.html', logs=logs)


@email_report_bp.route('/reports/<period>', methods=['GET'])
@login_required
def sales_reports_center(period: str):
    """
    报表中心：展示销售日报/周报/月报汇总（按店铺聚合），并提供发送按钮。
    - period in {daily, weekly, monthly}
    权限：仅管理员与财务可访问；店长/总店长/店���不可访问。
    """
    # 权限限制：仅管理员与财务可访问
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        flash('无权限访问报表中心', 'warning')
        return redirect(url_for('main.index'))

    period_map = {
        'daily': 'day',
        'weekly': 'week',
        'monthly': 'month'
    }
    if period not in period_map:
        return redirect(url_for('main.index'))

    p = period_map[period]

    # 解析查询参数
    store_id_arg = request.args.get('store_id')
    start_date_arg = request.args.get('start_date')
    end_date_arg = request.args.get('end_date')

    # 初始化避免未赋值引用
    stores = []
    report_data = []
    total_data = None
    period_str = ''
    last_period_str = ''

    def parse_date_safe(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None

    # 基于 period 的默认统计区间
    today = date.today()
    if p == 'day':
        default_start = default_end = today - timedelta(days=1)
    elif p == 'week':
        weekday = today.weekday()  # 0=周一
        last_sun = today - timedelta(days=weekday + 1)
        default_start = last_sun - timedelta(days=6)
        default_end = last_sun
    else:  # month
        last_month = (today.replace(day=1) - timedelta(days=1))
        default_start = date(last_month.year, last_month.month, 1)
        default_end = date(last_month.year, last_month.month, last_month.day)

    # 若提供了日期/店铺筛选，采用���松聚合路径
    start_date_sel = parse_date_safe(start_date_arg) or default_start
    end_date_sel = parse_date_safe(end_date_arg) or default_end
    filtered = bool(store_id_arg or start_date_arg or end_date_arg)

    def format_period_str(s: date, e: date, per: str) -> Tuple[str, str]:
        if per == 'day' and s == e:
            period_str_ = s.strftime('%Y-%m-%d')
            last_period_str_ = (s - timedelta(days=1)).strftime('%Y-%m-%d')
            return period_str_, last_period_str_
        # 通用范围
        period_str_ = f"{s.strftime('%Y-%m-%d')} ~ {e.strftime('%Y-%m-%d')}"
        span_days = (e - s).days + 1
        prev_end = s - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span_days - 1)
        last_period_str_ = f"{prev_start.strftime('%Y-%m-%d')} ~ {prev_end.strftime('%Y-%m-%d')}"
        return period_str_, last_period_str_

    data_incomplete = False

    if not filtered:
        # 先尝试复用邮件统计逻辑（对数据完整性有严格要求）
        stores, report_data, total_data, period_str, last_period_str = query_sales_reports(p, current_user.role,
                                                                                           current_user)
        if total_data is None:
            # 数据不完整时，回退到直接查询，放宽完整性要求，仅用于页面展示
            data_incomplete = True
            start_date_sel, end_date_sel = default_start, default_end
    # 宽松聚合：当筛选存在或上一步数据不完整
    if filtered or total_data is None:
        # 门店范围（管理员/财务：全部门店；可��店铺筛选）
        store_query = Store.query
        if store_id_arg:
            store_query = store_query.filter(Store.store_id == store_id_arg)
        stores = store_query.order_by(Store.store_id.asc()).all()

        # 聚合查询（可选按店铺筛选，不强制所有门店都有数据）
        rows_q = db.session.query(
            DailySales.store_id,
            func.sum(func.coalesce(DailySales.pos_total, 0) + func.coalesce(DailySales.takeaway_amount, 0)).label(
                'theory_sales'),
            func.sum(DailySales.takeaway_amount).label('takeaway'),
            func.sum(DailySales.actual_sales).label('actual_sales'),
            func.sum(DailySales.total_error).label('error'),
            # 新增：电子支付相关统计
            func.sum(DailySales.pos_income).label('total_pos_income'),
            func.sum(DailySales.electronic_actual_arrival).label('total_electronic_actual'),
            func.sum(DailySales.bank_deposit).label('total_bank_deposit'),
            func.sum(DailySales.bank_fee).label('total_bank_fee'),
            func.sum(DailySales.cash_income).label('total_cash_income')
        ).filter(
            DailySales.report_date >= start_date_sel,
            DailySales.report_date <= end_date_sel,
            DailySales.financial_check_status == FinancialCheckStatus.APPROVED
        )
        if store_id_arg:
            rows_q = rows_q.filter(DailySales.store_id == store_id_arg)
        rows_q = rows_q.group_by(DailySales.store_id).all()

        report_data = []
        total_data = {
            'total_theory': 0.0,
            'total_takeaway': 0.0,
            'total_actual': 0.0,
            'total_error': 0.0,
            'theory_diff': 0.0,
            # 新增：电子支付统计汇总
            'total_pos_income': 0.0,
            'total_electronic_actual': 0.0,
            'total_bank_deposit': 0.0,
            'total_bank_fee': 0.0,
            'total_cash_income': 0.0,
            'electronic_variance': 0.0,  # 电子支付差异
            'bank_efficiency': 0.0  # 银行存款效率
        }
        for r in rows_q:
            # 计算电子支付差异：实际到账 - POS显示金额
            electronic_variance = float(r.total_electronic_actual or 0) - float(r.total_pos_income or 0)
            # 计算银行存款效率：存款金额 / (存款金额 + 手续费) * 100
            bank_total = float(r.total_bank_deposit or 0) + float(r.total_bank_fee or 0)
            bank_efficiency = (float(r.total_bank_deposit or 0) / bank_total * 100) if bank_total > 0 else 0

            report_data.append({
                'store_id': r.store_id,
                'theory_sales': float(r.theory_sales or 0),
                'takeaway': float(r.takeaway or 0),
                'actual_sales': float(r.actual_sales or 0),
                'error': float(r.error or 0),
                # 新增字段
                'pos_income': float(r.total_pos_income or 0),
                'electronic_actual': float(r.total_electronic_actual or 0),
                'bank_deposit': float(r.total_bank_deposit or 0),
                'bank_fee': float(r.total_bank_fee or 0),
                'cash_income': float(r.total_cash_income or 0),
                'electronic_variance': electronic_variance,
                'bank_efficiency': bank_efficiency
            })
            total_data['total_theory'] += float(r.theory_sales or 0)
            total_data['total_takeaway'] += float(r.takeaway or 0)
            total_data['total_actual'] += float(r.actual_sales or 0)
            total_data['total_error'] += float(r.error or 0)
            # 新增汇总
            total_data['total_pos_income'] += float(r.total_pos_income or 0)
            total_data['total_electronic_actual'] += float(r.total_electronic_actual or 0)
            total_data['total_bank_deposit'] += float(r.total_bank_deposit or 0)
            total_data['total_bank_fee'] += float(r.total_bank_fee or 0)
            total_data['total_cash_income'] += float(r.total_cash_income or 0)

        # 计算总体电子支付差异和银行存款效率
        total_data['electronic_variance'] = total_data['total_electronic_actual'] - total_data['total_pos_income']
        total_bank_total = total_data['total_bank_deposit'] + total_data['total_bank_fee']
        total_data['bank_efficiency'] = (
                total_data['total_bank_deposit'] / total_bank_total * 100) if total_bank_total > 0 else 0

        period_str, last_period_str = format_period_str(start_date_sel, end_date_sel, p)

    # 将 report_data 聚合为"按店铺"的汇总
    per_store = {}
    for r in (report_data or []):
        sid = r.get('store_id') or r.get('store', '')
        if sid not in per_store:
            per_store[sid] = {
                'theory_sales': 0.0, 'actual_sales': 0.0, 'takeaway': 0.0, 'error': 0.0,
                'pos_income': 0.0, 'electronic_actual': 0.0, 'bank_deposit': 0.0,
                'bank_fee': 0.0, 'cash_income': 0.0, 'electronic_variance': 0.0, 'bank_efficiency': 0.0
            }
        per_store[sid]['theory_sales'] += float(r.get('theory_sales') or 0)
        per_store[sid]['actual_sales'] += float(r.get('actual_sales') or 0)
        per_store[sid]['takeaway'] += float(r.get('takeaway') or 0)
        per_store[sid]['error'] += float(r.get('error') or 0)
        # 新增字段聚合
        per_store[sid]['pos_income'] += float(r.get('pos_income') or 0)
        per_store[sid]['electronic_actual'] += float(r.get('electronic_actual') or 0)
        per_store[sid]['bank_deposit'] += float(r.get('bank_deposit') or 0)
        per_store[sid]['bank_fee'] += float(r.get('bank_fee') or 0)
        per_store[sid]['cash_income'] += float(r.get('cash_income') or 0)

    store_map = {s.store_id: s.store_name for s in (stores or [])}
    rows = []
    for sid in per_store.keys():
        # 重新计算每个店铺的电子支付差异和银行存款效率
        store_data = per_store[sid]
        electronic_variance = store_data['electronic_actual'] - store_data['pos_income']
        bank_total = store_data['bank_deposit'] + store_data['bank_fee']
        bank_efficiency = (store_data['bank_deposit'] / bank_total * 100) if bank_total > 0 else 0

        rows.append({
            'store_id': sid,
            'store_name': store_map.get(sid, sid),
            'theory_sales': store_data['theory_sales'],
            'actual_sales': store_data['actual_sales'],
            'takeaway': store_data['takeaway'],
            'error': store_data['error'],
            # 新增展示字段
            'pos_income': store_data['pos_income'],
            'electronic_actual': store_data['electronic_actual'],
            'bank_deposit': store_data['bank_deposit'],
            'bank_fee': store_data['bank_fee'],
            'cash_income': store_data['cash_income'],
            'electronic_variance': electronic_variance,
            'bank_efficiency': bank_efficiency
        })

    rows.sort(key=lambda x: x['theory_sales'], reverse=True)

    page_title = {'day': '销售日报', 'week': '销售周报', 'month': '销售月报'}.get(p, '销售报表')

    # 用于筛选��单回显
    start_date_str = (start_date_sel or default_start).strftime('%Y-%m-%d')
    end_date_str = (end_date_sel or default_end).strftime('%Y-%m-%d')

    return render_template(
        'email_report/report_center.html',
        period=p,
        page_title=page_title,
        period_str=period_str,
        last_period_str=last_period_str,
        total_data=total_data,
        rows=rows,
        data_incomplete=data_incomplete,
        stores=stores,
        selected_store_id=store_id_arg or '',
        start_date_str=start_date_str,
        end_date_str=end_date_str
    )


@email_report_bp.route('/reports/send_now', methods=['POST'])
@login_required
def send_report_now():
    """
    从报表中心手动发送当前周期报表到当前用户邮箱。
    权限：仅管理员与财务可触发；其它角色不可触发。
    """
    # 权限限制：仅管理员与财务可触发
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        flash('无权限执行该操作', 'warning')
        return redirect(url_for('main.index'))

    p = request.form.get('period', 'day')
    if p not in ('day', 'week', 'month'):
        flash('无效的报表类型', 'warning')
        return redirect(url_for('main.index'))

    recipient = getattr(current_user, 'email', None)
    if not recipient:
        flash('当前用户未配置邮箱，无法发送邮件', 'warning')
        back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
        return redirect(url_for('email_report.sales_reports_center', period=back))

    ok = send_sales_report_mail(p, current_user.role, current_user, [recipient])
    flash('邮件已发送到您的邮箱' if ok else '数据不完整或发送失败，请稍后重试', 'success' if ok else 'danger')
    back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
    return redirect(url_for('email_report.sales_reports_center', period=back))


# 新增：自定义发送（指定收件人或按角色发送）
@email_report_bp.route('/reports/send_custom', methods=['POST'])
@login_required
def send_report_custom():
    # 权限限制
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        flash('无权限执行该操作', 'warning')
        return redirect(url_for('main.index'))

    p = request.form.get('period', 'day')
    if p not in ('day', 'week', 'month'):
        flash('无效的报表类型', 'warning')
        return redirect(url_for('main.index'))

    mode = request.form.get('send_mode', 'custom')  # custom | by_role
    if mode == 'by_role':
        roles = request.form.getlist('roles')  # 例如 ['ADMIN','FINANCE']
        if not roles:
            flash('请至少选择一个角色', 'warning')
            back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
            return redirect(url_for('email_report.sales_reports_center', period=back))
        # 批量按角色发送
        success_count = fail_count = 0
        for r in roles:
            try:
                role_enum = RoleType[r]
            except Exception:
                continue
            users = User.query.filter(User.role == role_enum).all()
            for u in users:
                ok = send_sales_report_mail(p, u.role, u, [u.email])
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
        if fail_count and success_count:
            flash(f'部分发送失败：成功{success_count}，失败{fail_count}', 'warning')
        elif fail_count and not success_count:
            flash('发送失败，请稍后重试', 'danger')
        else:
            flash(f'发送成功，共{success_count}封', 'success')
    else:
        # 指定收件人
        recipients_raw = request.form.get('recipients', '')
        recipients = [x.strip() for x in recipients_raw.replace(';', ',').split(',') if x.strip()]
        if not recipients:
            flash('���填写至少一个收件人邮箱', 'warning')
            back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
            return redirect(url_for('email_report.sales_reports_center', period=back))
        ok = send_sales_report_mail(p, current_user.role, current_user, recipients)
        flash('发送成功' if ok else '数据不完整或发送失败，请稍后重试', 'success' if ok else 'danger')

    back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
    return redirect(url_for('email_report.sales_reports_center', period=back))


# 新增：邮件内容预览（返回HTML片段）
@email_report_bp.route('/reports/preview', methods=['GET'])
@login_required
def preview_report_html():
    # 权限限制
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        return Response('无权���', status=403)

    p = request.args.get('period', 'day')
    if p not in ('day', 'week', 'month'):
        return Response('参数错误', status=400)

    store_id_arg = request.args.get('store_id')
    start_date_arg = request.args.get('start_date')
    end_date_arg = request.args.get('end_date')

    def parse_date_safe(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None

    # 默认周期与选择周期
    today = date.today()
    if p == 'day':
        default_start = default_end = today - timedelta(days=1)
    elif p == 'week':
        weekday = today.weekday()
        last_sun = today - timedelta(days=weekday + 1)
        default_start = last_sun - timedelta(days=6)
        default_end = last_sun
    else:
        last_month = (today.replace(day=1) - timedelta(days=1))
        default_start = date(last_month.year, last_month.month, 1)
        default_end = date(last_month.year, last_month.month, last_month.day)

    start_date_sel = parse_date_safe(start_date_arg) or default_start
    end_date_sel = parse_date_safe(end_date_arg) or default_end

    # 构建门店范围
    store_query = Store.query
    if store_id_arg:
        store_query = store_query.filter(Store.store_id == store_id_arg)
    stores = store_query.order_by(Store.store_id.asc()).all()

    # 组装按日期+店铺的明细（与邮件表格一致）
    sales_rows = db.session.query(
        DailySales.store_id,
        DailySales.report_date,
        db.func.sum(db.func.coalesce(DailySales.pos_total, 0) + db.func.coalesce(DailySales.takeaway_amount, 0)).label(
            'theory_sales'),
        db.func.sum(DailySales.takeaway_amount).label('takeaway'),
        db.func.sum(DailySales.actual_sales).label('actual_sales'),
        db.func.sum(DailySales.total_error).label('error')
    ).filter(
        DailySales.report_date >= start_date_sel,
        DailySales.report_date <= end_date_sel,
        DailySales.financial_check_status == FinancialCheckStatus.APPROVED
    )
    if store_id_arg:
        sales_rows = sales_rows.filter(DailySales.store_id == store_id_arg)
    sales_rows = sales_rows.group_by(DailySales.store_id, DailySales.report_date).order_by(
        DailySales.report_date.asc(), DailySales.store_id.asc()
    ).all()

    report_data = []
    total_actual = total_error = total_theory = total_takeaway = 0.0
    for row in sales_rows:
        report_data.append({
            'date': row.report_date.strftime('%Y-%m-%d'),
            'store_id': row.store_id,
            'theory_sales': float(row.theory_sales or 0),
            'takeaway': float(row.takeaway or 0),
            'actual_sales': float(row.actual_sales or 0),
            'error': float(row.error or 0),
        })
        total_actual += float(row.actual_sales or 0)
        total_error += float(row.error or 0)
        total_theory += float(row.theory_sales or 0)
        total_takeaway += float(row.takeaway or 0)

    # 计算环比区间并计算理论营业额用于差值
    span_days = (end_date_sel - start_date_sel).days + 1
    prev_end = start_date_sel - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span_days - 1)
    last_total_theory = db.session.query(
        db.func.sum(db.func.coalesce(DailySales.pos_total, 0) + db.func.coalesce(DailySales.takeaway_amount, 0))
    ).filter(
        DailySales.report_date >= prev_start,
        DailySales.report_date <= prev_end,
        DailySales.financial_check_status == FinancialCheckStatus.APPROVED,
        (DailySales.store_id == store_id_arg) if store_id_arg else True
    ).scalar() or 0.0

    total_data = {
        'total_theory': float(total_theory),
        'total_takeaway': float(total_takeaway),
        'total_actual': float(total_actual),
        'total_error': float(total_error),
        'theory_diff': float(total_theory) - float(last_total_theory)
    }

    # 周期字符串
    if p == 'day' and start_date_sel == end_date_sel:
        period_str = start_date_sel.strftime('%Y-%m-%d')
        last_period_str = (start_date_sel - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        period_str = f"{start_date_sel.strftime('%Y-%m-%d')} ~ {end_date_sel.strftime('%Y-%m-%d')}"
        last_period_str = f"{prev_start.strftime('%Y-%m-%d')} ~ {prev_end.strftime('%Y-%m-%d')}"

    html = render_sales_report_html(p, report_data, total_data, period_str, last_period_str)
    return Response(html, mimetype='text/html')


# 新增：按筛选条件发送（宽松聚合，不做完整性校验）
@email_report_bp.route('/reports/send_by_filters', methods=['POST'])
@login_required
def send_report_by_filters():
    # 权限限制
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        flash('无权限执行该操作', 'warning')
        return redirect(url_for('main.index'))

    p = request.form.get('period', 'day')
    if p not in ('day', 'week', 'month'):
        flash('无效���报表类型', 'warning')
        return redirect(url_for('main.index'))

    # 读取筛选参数（通过表单隐藏字段传入）
    store_id_arg = request.form.get('store_id') or None
    start_date_arg = request.form.get('start_date')
    end_date_arg = request.form.get('end_date')

    def parse_date_safe(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None

    # 默认周期
    today = date.today()
    if p == 'day':
        default_start = default_end = today - timedelta(days=1)
    elif p == 'week':
        weekday = today.weekday()
        last_sun = today - timedelta(days=weekday + 1)
        default_start = last_sun - timedelta(days=6)
        default_end = last_sun
    else:
        last_month = (today.replace(day=1) - timedelta(days=1))
        default_start = date(last_month.year, last_month.month, 1)
        default_end = date(last_month.year, last_month.month, last_month.day)

    start_date_sel = parse_date_safe(start_date_arg) or default_start
    end_date_sel = parse_date_safe(end_date_arg) or default_end

    # 构建明细和汇总（与预览一致，宽松）
    sales_rows = db.session.query(
        DailySales.store_id,
        DailySales.report_date,
        db.func.sum(db.func.coalesce(DailySales.pos_total, 0) + db.func.coalesce(DailySales.takeaway_amount, 0)).label(
            'theory_sales'),
        db.func.sum(DailySales.takeaway_amount).label('takeaway'),
        db.func.sum(DailySales.actual_sales).label('actual_sales'),
        db.func.sum(DailySales.total_error).label('error')
    ).filter(
        DailySales.report_date >= start_date_sel,
        DailySales.report_date <= end_date_sel,
        DailySales.financial_check_status == FinancialCheckStatus.APPROVED
    )
    if store_id_arg:
        sales_rows = sales_rows.filter(DailySales.store_id == store_id_arg)
    sales_rows = sales_rows.group_by(DailySales.store_id, DailySales.report_date).order_by(
        DailySales.report_date.asc(), DailySales.store_id.asc()
    ).all()

    report_data = []
    total_actual = total_error = total_theory = total_takeaway = 0.0
    for row in sales_rows:
        report_data.append({
            'date': row.report_date.strftime('%Y-%m-%d'),
            'store_id': row.store_id,
            'theory_sales': float(row.theory_sales or 0),
            'takeaway': float(row.takeaway or 0),
            'actual_sales': float(row.actual_sales or 0),
            'error': float(row.error or 0),
        })
        total_actual += float(row.actual_sales or 0)
        total_error += float(row.error or 0)
        total_theory += float(row.theory_sales or 0)
        total_takeaway += float(row.takeaway or 0)

    # 计算环比区间并计算理论营业额用于差值
    span_days = (end_date_sel - start_date_sel).days + 1
    prev_end = start_date_sel - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span_days - 1)
    last_total_theory = db.session.query(
        db.func.sum(db.func.coalesce(DailySales.pos_total, 0) + db.func.coalesce(DailySales.takeaway_amount, 0))
    ).filter(
        DailySales.report_date >= prev_start,
        DailySales.report_date <= prev_end,
        DailySales.financial_check_status == FinancialCheckStatus.APPROVED,
        (DailySales.store_id == store_id_arg) if store_id_arg else True
    ).scalar() or 0.0

    total_data = {
        'total_theory': float(total_theory),
        'total_takeaway': float(total_takeaway),
        'total_actual': float(total_actual),
        'total_error': float(total_error),
        'theory_diff': float(total_theory) - float(last_total_theory)
    }

    # 周期字符串
    if p == 'day' and start_date_sel == end_date_sel:
        period_str = start_date_sel.strftime('%Y-%m-%d')
        last_period_str = (start_date_sel - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        period_str = f"{start_date_sel.strftime('%Y-%m-%d')} ~ {end_date_sel.strftime('%Y-%m-%d')}"
        last_period_str = f"{prev_start.strftime('%Y-%m-%d')} ~ {prev_end.strftime('%Y-%m-%d')}"

    html = render_sales_report_html(p, report_data, total_data, period_str, last_period_str)

    # 读取发送模式与收件人
    mode = request.form.get('send_mode', 'custom')  # custom | by_role
    recipients: list[str] = []
    if mode == 'by_role':
        roles = request.form.getlist('roles')
        for r in roles:
            try:
                role_enum = RoleType[r]
            except Exception:
                continue
            users = User.query.filter(User.role == role_enum).all()
            recipients.extend([u.email for u in users if getattr(u, 'email', None)])
    else:
        recipients_raw = request.form.get('recipients', '')
        # 兼容逗号/分号分隔
        for token in recipients_raw.replace('；', ';').replace('，', ',').replace(';', ',').split(','):
            t = (token or '').strip()
            if t:
                recipients.append(t)

    if not recipients:
        flash('请填写至少一个有效收件人或选择角色', 'warning')
        back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
        return redirect(url_for('email_report.sales_reports_center', period=back))

    # 发送邮件（使用系统通知发送器）
    subj_map = {'day': '销售日报', 'week': '销售周报', 'month': '销售月报'}
    subject = f"【{subj_map.get(p, '销售报表')}】{period_str} 汇总信息（按筛选）"
    ok = send_notify_mail(subject, recipients, body='请查收销售报表（按筛选条件）。', html=html)

    if ok:
        flash(f'发送成功，共{len(recipients)}封', 'success')
    else:
        flash('发送失败，请稍后重试', 'danger')

    back = {'day': 'daily', 'week': 'weekly', 'month': 'monthly'}[p]
    return redirect(url_for('email_report.sales_reports_center', period=back))


@email_report_bp.route('/email_report/smtp_check', methods=['GET'])
@login_required
def smtp_check():
    # 仅管理员与财务
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        return Response('无权限', status=403)
    cfg = current_app.config
    server = cfg.get('MAIL_SERVER')
    port = int(cfg.get('MAIL_PORT') or 0)
    use_ssl = bool(cfg.get('MAIL_USE_SSL'))
    use_tls = bool(cfg.get('MAIL_USE_TLS'))
    username = cfg.get('MAIL_USERNAME')
    password = cfg.get('MAIL_PASSWORD')
    if not (server and port and username and password):
        return jsonify(ok=False, error='邮件配置不完整'), 200

    def try_login(srv: str, prt: int, ssl_on: bool, tls_on: bool):
        try:
            if ssl_on:
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(srv, prt, context=ctx, timeout=15) as smtp:
                    smtp.login(username, password)
            else:
                with smtplib.SMTP(srv, prt, timeout=15) as smtp:
                    smtp.ehlo()
                    if tls_on:
                        smtp.starttls(context=ssl.create_default_context())
                        smtp.ehlo()
                    smtp.login(username, password)
            return True, None
        except Exception as e:
            return False, str(e)

    # 先用当前配置
    ok, err = try_login(server, port, use_ssl, use_tls)
    if ok:
        return jsonify(ok=True, server=server, port=port, ssl=use_ssl, tls=use_tls), 200

    # 失败则尝试常见组合
    candidates = []
    # 优先尝试 465+SSL
    candidates.append({'server': server, 'port': 465, 'ssl': True, 'tls': False})
    # 再尝试 587+TLS
    candidates.append({'server': server, 'port': 587, 'ssl': False, 'tls': True})
    # 如果当前就是其中之一，会重复尝试没关系
    for c in candidates:
        ok2, err2 = try_login(c['server'], c['port'], c['ssl'], c['tls'])
        if ok2:
            return jsonify(
                ok=False,
                error=err,
                server=server,
                port=port,
                ssl=use_ssl,
                tls=use_tls,
                suggestion={
                    'server': c['server'],
                    'port': c['port'],
                    'ssl': c['ssl'],
                    'tls': c['tls'],
                    'username_equals_sender': True
                }
            ), 200

    # 都失败，返回最后错误
    current_app.logger.error(f"SMTP自检失败: {err}")
    return jsonify(ok=False, error=err, server=server, port=port, ssl=use_ssl, tls=use_tls), 200


# 新增：成本统计中心（按报销数据聚合）
@email_report_bp.route('/reports/costs', methods=['GET'])
@login_required
def cost_reports_center():
    """
    报表中心 - 成本统计（按店铺汇总）
    仅管理员与财务可访问。数据来源为报销模块（已审批的报销申请），按审批时间聚合。
    支持按店铺和时间区间筛选，默认统计上个月���
    """
    # 权限限制：仅管理员与财务可访问
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        flash('无权限访问报表中心', 'warning')
        return redirect(url_for('main.index'))

    # 解析查询参数
    store_id_arg = request.args.get('store_id')
    start_date_arg = request.args.get('start_date')
    end_date_arg = request.args.get('end_date')

    def parse_date_safe(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None

    # 默认：上个月整月
    today = date.today()
    last_month = (today.replace(day=1) - timedelta(days=1))
    default_start = date(last_month.year, last_month.month, 1)
    default_end = date(last_month.year, last_month.month, last_month.day)

    start_date_sel = parse_date_safe(start_date_arg) or default_start
    end_date_sel = parse_date_safe(end_date_arg) or default_end

    # 门店列表供筛选 - 始终读取全部门店用于下拉框回显和切换，数据筛选由后续查询使用 store_id_arg 控制
    stores = Store.query.order_by(Store.store_id.asc()).all()

    # 预先初始化 shared_total，防止在某些分支中被引用时尚未赋值导致 UnboundLocalError
    shared_total = 0.0

    # 按店铺聚合报销金额（仅 APPROVED 并且有 approved_at 时间，且店铺存在）
    rows_q = db.session.query(
        ReimbursementRequest.store_id,
        func.sum(ReimbursementRequest.amount).label('total_amount')
    ).join(
        Store, ReimbursementRequest.store_id == Store.store_id
    ).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )
    if store_id_arg:
        rows_q = rows_q.filter(ReimbursementRequest.store_id == store_id_arg)
    rows_q = rows_q.group_by(ReimbursementRequest.store_id).all()

    # 将查询结果转换为按店铺的字典，便于补齐没有报销记录的店铺
    cost_by_store = { (r.store_id or ''): float(r.total_amount or 0) for r in rows_q }

    rows = []
    total_amount = 0.0
    # 如果前端传入了 store_id，则仅展示该店（即使其无报销记录也应显示）；
    # 否则展示所有门店，未出现于 cost_by_store 的店铺 total_amount 为 0
    if store_id_arg:
        # 尝试读取该店的信息以保证回显名称正确
        single_store = Store.query.filter(Store.store_id == store_id_arg).first()
        sid = single_store.store_id if single_store else (store_id_arg or '')
        amt = cost_by_store.get(sid, 0.0)
        rows.append({'store_id': sid, 'total_amount': amt})
        total_amount += amt
    else:
        for s in stores:
            sid = s.store_id or ''
            amt = cost_by_store.get(sid, 0.0)
            rows.append({'store_id': sid, 'total_amount': amt})
            total_amount += amt

    # ===== 计算公摊成本（一级分类）并进行分摊 =====
    # 公摊成本均等分摊到所有店铺

    # 计算公摊成本总额（primary_category == SHARED_COST）
    shared_total_query = db.session.query(func.sum(ReimbursementRequest.amount)).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.primary_category == ReimbursementPrimaryCategory.SHARED_COST,
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )

    # 公摊总额为全局共享成本总和，不应因为前端的 store_id 筛选而把共享记录排除
    shared_total = float(shared_total_query.scalar() or 0.0)

    # 调试信息：检查公摊成本记录数量
    shared_count_query = db.session.query(func.count(ReimbursementRequest.request_id)).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.primary_category == ReimbursementPrimaryCategory.SHARED_COST,
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )

    shared_count = shared_count_query.scalar() or 0
    current_app.logger.info(f"[成本统计] 公摊成本记录数量: {shared_count}")
    current_app.logger.info(f"[成本统计] 公摊成本总额: {shared_total}")
    current_app.logger.info(f"[成本统计] 查询时间范围: {start_date_sel} ~ {end_date_sel}")
    current_app.logger.info(f"[成本统计] 筛选店铺: {store_id_arg}")

    # 按二级分类汇总
    categories = []
    # 如果前端按单个店铺筛选，则按该店铺的报销记录聚合，并把该店应分摊的公摊金额作为独立类别展示
    if store_id_arg:
        cat_q = db.session.query(
            ReimbursementRequest.secondary_category,
            func.sum(ReimbursementRequest.amount).label('cat_amount')
        ).filter(
            ReimbursementRequest.status == ReimbursementStatus.APPROVED,
            (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
            ReimbursementRequest.approved_at != None,
            ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
            ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time()),
            ReimbursementRequest.store_id == store_id_arg
        ).group_by(ReimbursementRequest.secondary_category).all()

        for c in cat_q:
            cat_name = getattr(c.secondary_category, 'value', str(c.secondary_category)) if c.secondary_category else '未分类'
            categories.append({'category': cat_name, 'amount': float(c.cat_amount or 0)})

        # 把该店的公摊份额作为单独的类别显示（均等分摊到所有店铺）
        total_stores = Store.query.count() or 0
        if total_stores > 0 and shared_total > 0:
            per_store_shared = float(shared_total) / total_stores
            categories.append({'category': '公摊', 'amount': per_store_shared})
    else:
        # 全局聚合（包含共享记录）
        cat_q = db.session.query(
            ReimbursementRequest.secondary_category,
            func.sum(ReimbursementRequest.amount).label('cat_amount')
        ).filter(
            ReimbursementRequest.status == ReimbursementStatus.APPROVED,
            (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
            ReimbursementRequest.approved_at != None,
            ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
            ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
        ).group_by(ReimbursementRequest.secondary_category).all()

        for c in cat_q:
            cat_name = getattr(c.secondary_category, 'value', str(c.secondary_category)) if c.secondary_category else '未分类'
            categories.append({'category': cat_name, 'amount': float(c.cat_amount or 0)})

    # 回显
    start_date_str = start_date_sel.strftime('%Y-%m-%d')
    end_date_str = end_date_sel.strftime('%Y-%m-%d')

    # 将店铺名称映射
    store_map = {s.store_id: s.store_name for s in (stores or [])}
    for row in rows:
        row['store_name'] = store_map.get(row['store_id'], row['store_id'])

    # 按金额降序排序
    rows.sort(key=lambda x: x['total_amount'], reverse=True)

    period_str = f"{start_date_str} ~ {end_date_str}" if start_date_sel != end_date_sel else start_date_str

    # 调试信息：检查公摊成本记录数量
    shared_count_query = db.session.query(func.count(ReimbursementRequest.request_id)).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED,
        ReimbursementRequest.primary_category == ReimbursementPrimaryCategory.SHARED_COST,
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )

    shared_count = shared_count_query.scalar() or 0
    current_app.logger.info(f"[成本统计] 公摊成本记录数量: {shared_count}")
    current_app.logger.info(f"[成本统计] 公摊成本总额: {shared_total}")
    current_app.logger.info(f"[成本统计] 查询时间范围: {start_date_sel} ~ {end_date_sel}")
    current_app.logger.info(f"[成本统计] 筛选店铺: {store_id_arg}")

    # 调试信息：检查所有报销记录统计
    total_records = db.session.query(func.count(ReimbursementRequest.request_id)).join(
        Store, ReimbursementRequest.store_id == Store.store_id
    ).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )
    if store_id_arg:
        total_records = total_records.filter(ReimbursementRequest.store_id == store_id_arg)
    
    total_count = total_records.scalar() or 0
    current_app.logger.info(f"[成本统计] 符合条件的总记录数: {total_count}")

    # 调试：直接查询公摊成本记录
    shared_records = db.session.query(ReimbursementRequest).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.primary_category == ReimbursementPrimaryCategory.SHARED_COST,
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )

    shared_list = shared_records.all()
    current_app.logger.info(f"[成本统计] 公摊成本记录详情: {[(r.request_id, r.amount, r.store_id) for r in shared_list]}")

    # 取每店的理论营业额作为分摊权重（若无则为0）
    sales_q = db.session.query(
        DailySales.store_id,
        func.sum(func.coalesce(DailySales.pos_total, 0) + func.coalesce(DailySales.takeaway_amount, 0)).label('theory')
    ).filter(
        DailySales.report_date >= start_date_sel,
        DailySales.report_date <= end_date_sel,
        DailySales.financial_check_status == FinancialCheckStatus.APPROVED
    )
    if store_id_arg:
        sales_q = sales_q.filter(DailySales.store_id == store_id_arg)
    sales_q = sales_q.group_by(DailySales.store_id).all()
    store_theory = {r.store_id: float(r.theory or 0.0) for r in sales_q}

    # 分摊到所有店铺（均等分摊）——始终以系统中全部店铺为分母
    store_ids = [r['store_id'] for r in rows]
    all_stores = Store.query.order_by(Store.store_id.asc()).all()
    target_stores = [s.store_id for s in all_stores] if all_stores else store_ids

    # 计算分摊：均等分摊到目标店铺集合
    allocation_map = {}
    per = 0.0
    if target_stores and shared_total > 0:
        per = shared_total / len(target_stores)
        for sid in target_stores:
            allocation_map[sid] = per

    # 调试信息：输出分摊计算结果
    current_app.logger.info(f"[成本统计] 目标店铺数量: {len(target_stores)}")
    current_app.logger.info(f"[成本统计] 每店分摊金额: {per if target_stores and shared_total > 0 else 0}")
    current_app.logger.info(f"[成本统计] 分摊映射: {allocation_map}")

    # 将分摊结果合并回 rows，计算含分摊的成本
    total_after_allocation = 0.0
    for row in rows:
        sid = row['store_id']
        alloc = float(allocation_map.get(sid, 0.0))
        row['allocated_shared'] = alloc
        row['cost_after_allocation'] = row['total_amount'] + alloc
        total_after_allocation += row['cost_after_allocation']

    # 传递共享总额给模板
    shared_info = {
        'shared_total': shared_total,
        'allocated_sum': sum(allocation_map.values())
    }

    return render_template('email_report/cost_report.html',
                           page_title='成本统计',
                           period_str=period_str,
                           total_amount=total_amount,
                           rows=rows,
                           categories=categories,
                           stores=stores,
                           selected_store_id=store_id_arg or '',
                           start_date_str=start_date_str,
                           end_date_str=end_date_str,
                           shared_info=shared_info,
                           total_after_allocation=total_after_allocation)


@email_report_bp.route('/profit_loss_reports', methods=['GET'])
@login_required
def profit_loss_reports_center():
    """
    报表中心 - 损益报表（按店铺汇总）
    仅管理员与财务可访问。计算各店铺的纯利润盈亏信息。
    收入来源：销售数据（DailySales.actual_sales）
    成本来源：报销数据（已审批的报销申请）
    支持按店铺和时间区间筛选，默认统计上个月。
    """
    # 权限限制：仅管理员与财务可访问
    if current_user.role not in (RoleType.ADMIN, RoleType.FINANCE):
        flash('无权限访问报表中心', 'warning')
        return redirect(url_for('main.index'))

    # 解析查询参数
    store_id_arg = request.args.get('store_id')
    start_date_arg = request.args.get('start_date')
    end_date_arg = request.args.get('end_date')

    def parse_date_safe(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d').date()
        except Exception:
            return None

    # 默认：上个月整月
    today = date.today()
    last_month = (today.replace(day=1) - timedelta(days=1))
    default_start = date(last_month.year, last_month.month, 1)
    default_end = date(last_month.year, last_month.month, last_month.day)

    start_date_sel = parse_date_safe(start_date_arg) or default_start
    end_date_sel = parse_date_safe(end_date_arg) or default_end

    # 门店列表供筛选
    store_query = Store.query
    if store_id_arg:
        store_query = store_query.filter(Store.store_id == store_id_arg)
    stores = store_query.order_by(Store.store_id.asc()).all()

    # 1. 查询销售收入（从DailySales表）
    sales_query = db.session.query(
        DailySales.store_id,
        func.sum(DailySales.actual_sales).label('total_revenue')
    ).filter(
        DailySales.report_date >= start_date_sel,
        DailySales.report_date <= end_date_sel
    )
    if store_id_arg:
        sales_query = sales_query.filter(DailySales.store_id == store_id_arg)
    sales_data = sales_query.group_by(DailySales.store_id).all()

    # 2. 查询成本支出（从ReimbursementRequest表）
    cost_query = db.session.query(
        ReimbursementRequest.store_id,
        func.sum(ReimbursementRequest.amount).label('total_cost')
    ).join(
        Store, ReimbursementRequest.store_id == Store.store_id
    ).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )
    if store_id_arg:
        cost_query = cost_query.filter(ReimbursementRequest.store_id == store_id_arg)
    cost_data = cost_query.group_by(ReimbursementRequest.store_id).all()

    # 3. 整合数据：构建店铺损益表
    store_map = {s.store_id: s.store_name for s in stores}

    # 创建收入字典
    revenue_dict = {s.store_id: float(s.total_revenue or 0) for s in sales_data}

    # 创建成本字典
    cost_dict = {c.store_id: float(c.total_cost or 0) for c in cost_data}

    # 获取所有有数据的店铺ID
    all_store_ids = set(revenue_dict.keys()) | set(cost_dict.keys())
    if store_id_arg:
        all_store_ids = {store_id_arg} & all_store_ids

    rows = []
    total_revenue = 0.0
    total_cost = 0.0
    total_profit = 0.0

    for store_id in sorted(all_store_ids):
        revenue = revenue_dict.get(store_id, 0.0)
        cost = cost_dict.get(store_id, 0.0)
        profit = revenue - cost
        profit_margin = (profit / revenue * 100) if revenue > 0 else 0.0

        rows.append({
            'store_id': store_id,
            'store_name': store_map.get(store_id, store_id),
            'total_revenue': revenue,
            'total_cost': cost,
            'profit': profit,
            'profit_margin': profit_margin
        })

        total_revenue += revenue
        total_cost += cost
        total_profit += profit

    # 按利润降序排序
    rows.sort(key=lambda x: x['profit'], reverse=True)

    # 总体利润率
    overall_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # 4. 按成本分类统计（用于饼图展示）
    category_query = db.session.query(
        ReimbursementRequest.secondary_category,
        func.sum(ReimbursementRequest.amount).label('cat_amount')
    ).join(
        Store, ReimbursementRequest.store_id == Store.store_id
    ).filter(
        ReimbursementRequest.status == ReimbursementStatus.APPROVED,
        (ReimbursementRequest.check_status == ReimbursementCheckStatus.CHECKED) | (ReimbursementRequest.check_status == None),
        ReimbursementRequest.approved_at != None,
        ReimbursementRequest.approved_at >= datetime.combine(start_date_sel, datetime.min.time()),
        ReimbursementRequest.approved_at <= datetime.combine(end_date_sel, datetime.max.time())
    )
    if store_id_arg:
        category_query = category_query.filter(ReimbursementRequest.store_id == store_id_arg)
    category_data = category_query.group_by(ReimbursementRequest.secondary_category).all()

    categories = []
    for c in category_data:
        cat_name = getattr(c.secondary_category, 'value', str(c.secondary_category)) if c.secondary_category else '未分类'
        categories.append({'category': cat_name, 'amount': float(c.cat_amount or 0)})

    # 回显参数
    start_date_str = start_date_sel.strftime('%Y-%m-%d')
    end_date_str = end_date_sel.strftime('%Y-%m-%d')
    period_str = f"{start_date_str} ~ {end_date_str}" if start_date_sel != end_date_sel else start_date_str

    # 汇总信息
    summary = {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'overall_profit_margin': overall_profit_margin,
        'store_count': len(rows)
    }

    return render_template('email_report/profit_loss_report.html',
                           page_title='损益报表',
                           period_str=period_str,
                           summary=summary,
                           rows=rows,
                           categories=categories,
                           stores=stores,
                           selected_store_id=store_id_arg or '',
                           start_date_str=start_date_str,
                           end_date_str=end_date_str)
