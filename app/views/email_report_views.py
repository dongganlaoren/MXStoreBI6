import os
from datetime import datetime
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash

from app.extensions import db
from app.models import User
from app.models.email_report_config import EmailReportConfig
from app.models.email_task_log import EmailTaskLog, EmailTaskType, EmailTaskStatus
from app.models.enums import RoleType
from app.utils.notify import send_sales_report_mail

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
    # 周报任务
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
        app.logger.info(f"[邮件任务] 开始执行 send_report_task, period={period}, roles={roles}")
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
                f"<span style='color:#5470C6;font-weight:600;'>{role_name}日报：</span>每天{info.daily_time}发送，统计前一天数据。")
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
