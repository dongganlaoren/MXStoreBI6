# app/utils/scheduler.py

import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app

from app.extensions import db
from app.utils.monitor import system_monitor, health_checker

# 创建后台调度器
scheduler = BackgroundScheduler()


def start_monitoring_tasks():
    """启动监控相关的定时任务"""

    # 每分钟收集系统指标
    scheduler.add_job(
        func=collect_system_metrics_job,
        trigger=IntervalTrigger(minutes=1),
        id='collect_metrics',
        name='收集系统指标',
        replace_existing=True
    )

    # 每5分钟执行健康检查
    scheduler.add_job(
        func=run_health_checks_job,
        trigger=IntervalTrigger(minutes=5),
        id='health_check',
        name='系统健康检查',
        replace_existing=True
    )

    # 每小时清理旧数据
    scheduler.add_job(
        func=cleanup_old_data_job,
        trigger=IntervalTrigger(hours=1),
        id='cleanup_data',
        name='清理旧数据',
        replace_existing=True
    )

    # 启动调度器
    scheduler.start()

    # 注册退出时关闭调度器
    atexit.register(lambda: scheduler.shutdown())


def collect_system_metrics_job():
    """系统指标收集任务"""
    try:
        with current_app.app_context():
            system_monitor.collect_system_metrics()
    except Exception as e:
        logging.error(f"系统指标收集任务失败: {e}")


def run_health_checks_job():
    """健康检查任务"""
    try:
        with current_app.app_context():
            health_checker.run_all_checks()
    except Exception as e:
        logging.error(f"健康检查任务失败: {e}")


def cleanup_old_data_job():
    """清理旧数据任务"""
    try:
        with current_app.app_context():
            from datetime import datetime, timedelta
            from app.models.system_monitor import SystemLog, SystemMetric, HealthCheck

            # 清理30天前的日志
            log_cutoff = datetime.utcnow() - timedelta(days=30)
            old_logs = SystemLog.query.filter(SystemLog.timestamp < log_cutoff).delete()

            # 清理7天前的系统指标
            metric_cutoff = datetime.utcnow() - timedelta(days=7)
            old_metrics = SystemMetric.query.filter(SystemMetric.timestamp < metric_cutoff).delete()

            # 清理7天前的健康检查记录
            health_cutoff = datetime.utcnow() - timedelta(days=7)
            old_health = HealthCheck.query.filter(HealthCheck.timestamp < health_cutoff).delete()

            db.session.commit()

            logging.info(f"清理完成: 日志 {old_logs} 条, 指标 {old_metrics} 条, 健康检查 {old_health} 条")

    except Exception as e:
        logging.error(f"数据清理任务失败: {e}")
        db.session.rollback()
