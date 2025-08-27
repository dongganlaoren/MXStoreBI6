# app/utils/notify.py
import re
import threading
from datetime import date, timedelta

import matplotlib

matplotlib.use('Agg')
from flask import current_app
from flask_mail import Message

from app.extensions import db, mail
from app.models import DailySales, Store, User, RoleType
from app.models.enums import FinancialCheckStatus


def send_async_email(app, msg):
    """异步发送邮件的辅助函数"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"异步邮件发送失败: {e}")


def _normalize_recipients(recipients):
    """接受 str 或 list，归一化为收件人列表：按中英文逗号/分号/空白分隔，去空白与空项，去重。"""
    items = []
    if isinstance(recipients, str):
        items = re.split(r"[\s,;，；]+", recipients)
    elif isinstance(recipients, (list, tuple, set)):
        for r in recipients:
            if isinstance(r, str):
                items.extend(re.split(r"[\s,;，；]+", r))
            else:
                items.append(r)
    else:
        items = [recipients]
    # 清洗
    cleaned = []
    seen = set()
    for it in items:
        if not isinstance(it, str):
            continue
        x = it.strip()
        if not x:
            continue
        if x not in seen:
            seen.add(x)
            cleaned.append(x)
    return cleaned


def send_notify_mail(subject, recipients, body, html=None, async_send=True):
    """
    发送系统通知邮件
    :param subject: 邮件主题
    :param recipients: 收件人列表或字符串（支持中英文逗号/分号/空白分隔）
    :param body: 邮件正文（纯文本）
    :param html: 邮件正文（HTML，可选）
    :param async_send: 是否异步发送，默认True
    :return: True/False
    """
    # 归一化收件人
    recipients = _normalize_recipients(recipients)
    # 过滤掉无效邮箱（仅非空，格式校验交给服务商）
    if not recipients:
        current_app.logger.info(f"邮件发送跳过：无有效收件人 subject={subject}")
        return True

    try:
        # 确保 sender 有效（优先使用默认发件人，缺失则回退用户名）
        sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        msg = Message(subject=subject,
                      recipients=recipients,
                      sender=sender,
                      body=body,
                      html=html)

        if async_send:
            # 异步发送邮件（推荐）
            thread = threading.Thread(
                target=send_async_email,
                args=(current_app._get_current_object(), msg)
            )
            thread.daemon = True
            thread.start()
            current_app.logger.info(f"邮件已提交异步发送队列 subject={subject} recipients={len(recipients)}")
        else:
            # 同步发送邮件（仅用于测试或特殊情况）
            mail.send(msg)
            current_app.logger.info(f"邮件同步发送成功 subject={subject} recipients={len(recipients)}")

        return True
    except Exception as e:
        current_app.logger.error(f"邮件发送失败: {e}")
        return False


# 测试函数（可在shell或视图中调用）
def test_send_mail():
    return send_notify_mail(
        subject="系统通知测试",
        recipients=["mirabi@163.com"],
        body="这是一封系统通知测试邮件。"
    )


def query_sales_reports(period: str, role: RoleType, user: User):
    """
    查询销售汇总数据，增加统计周期和环比数据
    :return: (门店列表, 每店报表数据, 汇总数据, 统计周期)
    """
    today = date.today()
    if period == 'day':
        # 日报统计周期为昨日，环比为前天
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
        last_start = today - timedelta(days=2)
        last_end = today - timedelta(days=2)
    elif period == 'week':
        # 统计周期：上一周（上周一到上周日），环比：上上周
        weekday = today.weekday()  # 0=周一
        last_sun = today - timedelta(days=weekday + 1)
        last_mon = last_sun - timedelta(days=6)
        start_date = last_mon
        end_date = last_sun
        prev_sun = last_mon - timedelta(days=1)
        prev_mon = prev_sun - timedelta(days=6)
        last_start = prev_mon
        last_end = prev_sun
    elif period == 'month':
        # 本月统计周期：上个月1号~上个月最后一天
        last_month = (today.replace(day=1) - timedelta(days=1))
        start_date = date(last_month.year, last_month.month, 1)
        end_date = date(last_month.year, last_month.month, last_month.day)
        # 环比周期：上上个月1号~上上月最后一天
        prev_month = (start_date - timedelta(days=1))
        last_start = date(prev_month.year, prev_month.month, 1)
        last_end = date(prev_month.year, prev_month.month, prev_month.day)
    else:
        raise ValueError('period参数错误')

    # 门店范围
    if role == RoleType.BRANCH_MANAGER:
        stores = Store.query.filter(Store.store_id == user.store_id).all()
    else:
        stores = Store.query.order_by(Store.store_id.asc()).all()

    report_data = []
    total_actual = total_error = total_theory = total_takeaway = 0.0
    last_total_theory = 0.0
    # 按日期和门店分组统计
    sales_rows = db.session.query(
        DailySales.store_id,
        DailySales.report_date,
        db.func.sum(DailySales.theoretical_total).label('theory_sales'),
        db.func.sum(DailySales.takeaway_amount).label('takeaway'),
        db.func.sum(DailySales.actual_sales).label('actual_sales'),
        db.func.sum(DailySales.total_error).label('error')
    ).filter(
        DailySales.report_date >= start_date,
        DailySales.report_date <= end_date,
        DailySales.financial_check_status == FinancialCheckStatus.APPROVED
    )
    if role == RoleType.BRANCH_MANAGER:
        sales_rows = sales_rows.filter(DailySales.store_id == user.store_id)
    sales_rows = sales_rows.group_by(DailySales.store_id, DailySales.report_date).order_by(DailySales.report_date.asc(),
                                                                                           DailySales.store_id.asc()).all()
    for row in sales_rows:
        report_data.append({
            'date': row.report_date.strftime('%Y-%m-%d'),
            'store_id': row.store_id,
            'theory_sales': row.theory_sales or 0,
            'takeaway': row.takeaway or 0,
            'actual_sales': row.actual_sales or 0,
            'error': row.error or 0
        })
        total_actual += row.actual_sales or 0
        total_error += row.error or 0
        total_theory += row.theory_sales or 0
        total_takeaway += row.takeaway or 0
    theory_diff = total_theory - last_total_theory

    # 销售统计数据完整性判断
    # 获取所有店ID
    all_store_ids = set([s.store_id for s in stores])
    # 获取本期所有有数据的门店ID
    reported_store_ids = set([row.store_id for row in sales_rows])
    # 判断是否所有门店都有数据
    is_data_complete = (all_store_ids == reported_store_ids)
    if not is_data_complete:
        # 数��不完整，推迟邮件发送（可抛出异常或返回特殊标记）
        return None, None, None, None, None

    # 统计周期字符串
    if period == 'day':
        period_str = start_date.strftime('%Y-%m-%d')
        last_period_str = last_start.strftime('%Y-%m-%d')
    elif period == 'week':
        period_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
        last_period_str = f"{last_start.strftime('%Y-%m-%d')} ~ {last_end.strftime('%Y-%m-%d')}"
    elif period == 'month':
        period_str = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
        last_period_str = f"{last_start.strftime('%Y-%m-%d')} ~ {last_end.strftime('%Y-%m-%d')}"
    # 返回5个值，兼容解包
    return stores, report_data, {
        'total_theory': total_theory,
        'total_takeaway': total_takeaway,
        'total_actual': total_actual,
        'total_error': total_error,
        'theory_diff': theory_diff
    }, period_str, last_period_str


def render_sales_report_html(period: str, report_data: list, total_data: dict, period_str: str, last_period_str: str):
    """
    按日报/周报/月报分别渲染邮件内容，货币符号为泰铢฿，销售明细用HTML表格展示
    """
    # 获取统计周的实际日期（日报为统计日期，周报/月报为周期字符串）
    if period == 'day':
        stat_date = period_str  # 昨天日期
    else:
        stat_date = period_str
    table_style = "border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-size:15px;width:100%;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(84,112,198,0.08);margin-bottom:10px;'"
    thead_style = "background:#f7f9fa;font-weight:600;color:#5470C6;"
    if period == 'day':
        title = f"销售日报"
        main_info = f"<div style='font-size:1.1rem;font-weight:bold;color:#5470C6;margin-bottom:10px;'>{stat_date}总营业额：฿{total_data['total_theory']:,.2f}</div>"
        main_info += f"<div style='font-size:1.1rem;font-weight:bold;color:#d43f3a;margin-bottom:10px;'>{stat_date}实际到账：฿{total_data['total_actual']:,.2f}</div>"
        main_info += f"<div style='font-size:1.1rem;font-weight:bold;color:#198754;margin-bottom:10px;'>营业额环比增长：฿{total_data['theory_diff']:,.2f}</div>"
        table_title = "销售明细表"
        if report_data:
            table_html = f"<div style='font-size:1.05rem;font-weight:600;margin:12px 0 6px 0;'>{table_title}</div>"
            table_html += f"<table {table_style}><thead style='{thead_style}'><tr><th>日期</th><th>店铺ID</th><th>理论营业额</th><th>实际到账</th><th>外卖</th><th>误差</th></tr></thead><tbody>"
            for r in report_data:
                table_html += f"<tr><td>{r.get('date', '')}</td><td>{r['store_id']}</td><td style='text-align:right'>{r.get('theory_sales', 0):,.2f}</td><td style='text-align:right'>{r.get('actual_sales', 0):,.2f}</td><td style='text-align:right'>{r.get('takeaway', 0):,.2f}</td><td style='text-align:right'>{r.get('error', 0):,.2f}</td></tr>"
            table_html += "</tbody></table>"
        else:
            table_html = "<div class='text-muted'>暂无销售明细数据</div>"
    elif period in ['week', 'month']:
        title = f"销售{'周报' if period == 'week' else '月报'}"
        main_info = f"<div style='font-size:1.1rem;font-weight:bold;color:#5470C6;margin-bottom:10px;'>本{'周' if period == 'week' else '月'}总营业额：฿{total_data['total_theory']:,.2f}</div>"
        main_info += f"<div style='font-size:1.1rem;font-weight:bold;color:#d43f3a;margin-bottom:10px;'>本{'周' if period == 'week' else '月'}���实际到账：฿{total_data['total_actual']:,.2f}</div>"
        main_info += f"<div style='font-size:1.1rem;font-weight:bold;color:#198754;margin-bottom:10px;'>营业额环比增长：฿{total_data['theory_diff']:,.2f}</div>"
        table_title = "销售明细表"
        if report_data:
            from collections import defaultdict
            grouped = defaultdict(list)
            for r in report_data:
                grouped[r['date']].append(r)
            table_html = f"<div style='font-size:1.05rem;font-weight:600;margin:12px 0 6px 0;'>{table_title}</div>"
            for day in sorted(grouped.keys()):
                table_html += f"<div style='margin:8px 0;font-weight:bold;color:#5470C6;'>{day}</div>"
                table_html += f"<table {table_style}><thead style='{thead_style}'><tr><th>店铺ID</th><th>理论营业额</th><th>实际到账</th><th>外卖</th><th>误差</th></tr></thead><tbody>"
                for r in grouped[day]:
                    table_html += f"<tr><td>{r['store_id']}</td><td style='text-align:right'>{r.get('theory_sales', 0):,.2f}</td><td style='text-align:right'>{r.get('actual_sales', 0):,.2f}</td><td style='text-align:right'>{r.get('takeaway', 0):,.2f}</td><td style='text-align:right'>{r.get('error', 0):,.2f}</td></tr>"
                table_html += "</tbody></table>"
        else:
            table_html = "<div class='text-muted'>暂无销售明细数据</div>"
    else:
        title = "销售汇总信息"
        main_info = ""
        table_title = "销售明细表"
        table_html = "<div class='text-muted'>���无销售明细数据</div>"
    html = f"""
    <h2 style='color:#5470C6;'>{title}</h2>
    <div style='margin-bottom:8px;'>统计周期：<b>{period_str}</b> &nbsp; 环比周期：<b>{last_period_str}</b></div>
    {main_info}
    {table_html}
    """
    return html


def send_sales_report_mail(period: str, role: RoleType, user: User, recipients: list):
    """
    发送销售汇总邮件（带统计周期和环比）
    """
    # 过滤掉无效邮箱
    recipients = [r for r in recipients if r]
    if not recipients:
        current_app.logger.info(f"销售报表邮件发送跳过：无有效收件人 period={period} role={role}")
        return True
    stores, report_data, total_data, period_str, last_period_str = query_sales_reports(period, role, user)
    if total_data is None:
        # 数据不完整，无法发送邮件
        current_app.logger.warning(f"销售报表邮件未发送：{period} {role} 数据不完整")
        return False
    html = render_sales_report_html(period, report_data, total_data, period_str, last_period_str)
    # 邮件标题增强，示例：【销售日报】2025-08-16 汇总信息
    period_map = {'day': '日报', 'week': '周报', 'month': '月报'}
    today_str = date.today().strftime('%Y-%m-%d')
    subject = f"【销售{period_map.get(period, '')}】{today_str} 汇总信息"
    body = f"请查收{subject}，详情见下表。"
    return send_notify_mail(subject, recipients, body, html)
