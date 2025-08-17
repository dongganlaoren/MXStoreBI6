# app/commands.py
from datetime import datetime, timedelta

import click
from flask import current_app
from flask.cli import with_appcontext

from app.extensions import db
from app.utils.fake_data import generate_fake_data


@click.command("fake-data")
@with_appcontext
def fake_data_command():
    """
    生成测试数据，并清理重复归档日报。
    """
    click.echo("开始生成测试数据...")
    generate_fake_data()
    click.echo("测试数据生成完毕！")


@click.command()
@with_appcontext
def init_monitoring():
    """初始化监控系统"""
    try:
        # 创建监控相关的数据库表
        from app.models.system_monitor import SystemLog, SystemMetric, SystemAlert, HealthCheck

        # 确保数据库表已创建
        db.create_all()

        # 创建测试告警规则
        click.echo("监控系统初始化完成！")
        click.echo("监控功能包括：")
        click.echo("- 系统日志记录")
        click.echo("- 性能指标监控")
        click.echo("- 告警管理")
        click.echo("- 健康检查")
        click.echo("访问 /monitor 查看监控仪表盘")

    except Exception as e:
        click.echo(f"监控系统初始化���败: {e}")


@click.command()
@with_appcontext
def cleanup_monitoring_data():
    """清理监控数据"""
    try:
        from app.models.system_monitor import SystemLog, SystemMetric, HealthCheck

        # 获取配置的数据保留天数
        log_retention_days = current_app.config.get('MONITORING_DATA_RETENTION_DAYS', 30)
        metric_retention_days = current_app.config.get('MONITORING_METRICS_RETENTION_DAYS', 7)

        # 清理旧日志
        log_cutoff = datetime.utcnow() - timedelta(days=log_retention_days)
        deleted_logs = SystemLog.query.filter(SystemLog.timestamp < log_cutoff).delete()

        # 清理旧指标
        metric_cutoff = datetime.utcnow() - timedelta(days=metric_retention_days)
        deleted_metrics = SystemMetric.query.filter(SystemMetric.timestamp < metric_cutoff).delete()

        # 清理旧健康检查记录
        health_cutoff = datetime.utcnow() - timedelta(days=metric_retention_days)
        deleted_health = HealthCheck.query.filter(HealthCheck.timestamp < health_cutoff).delete()

        db.session.commit()

        click.echo(f"数据清理完成:")
        click.echo(f"- 删除日志记录: {deleted_logs} 条")
        click.echo(f"- 删除指标记录: {deleted_metrics} 条")
        click.echo(f"- 删除健康检查记录: {deleted_health} 条")

    except Exception as e:
        click.echo(f"数据清理失败: {e}")
        db.session.rollback()


@click.command()
@with_appcontext
def test_monitoring():
    """测试监控系统功能"""
    try:
        # 测试系统指标收集
        from app.utils.monitor import system_monitor, health_checker

        click.echo("开始测试监控系统...")

        # 收集系统指标
        system_monitor.collect_system_metrics()
        click.echo("✓ 系统指标收集测试通过")

        # 执行健康检查
        health_results = health_checker.run_all_checks()
        click.echo("✓ 健康检查测试通过")

        # 获取系统状态
        status = system_monitor.get_system_status()
        click.echo(f"✓ 系统状态获取成功: {status['status']}")

        click.echo("监控系统测试完成！")

    except Exception as e:
        click.echo(f"监控系统测试失败: {e}")


@click.command()
@with_appcontext
def server_status():
    """检查服务器各组件状态"""
    try:
        from app.utils.monitor import health_checker

        click.echo("🔍 检查服务器组件状态...")
        results = health_checker.run_all_checks()

        click.echo("\n📊 服务状态报告:")
        click.echo("=" * 50)

        for service, result in results.items():
            status_icon = "✅" if result['status'] == 'OK' else "⚠️" if result['status'] == 'WARNING' else "❌"
            click.echo(f"{status_icon} {service:15} | {result['status']:8} | {result['message']}")

            if result.get('details') and isinstance(result['details'], dict):
                for key, value in result['details'].items():
                    if key not in ['error']:
                        click.echo(f"    └─ {key}: {value}")

        click.echo("=" * 50)

        # 统计概览
        ok_count = sum(1 for r in results.values() if r['status'] == 'OK')
        warning_count = sum(1 for r in results.values() if r['status'] == 'WARNING')
        error_count = sum(1 for r in results.values() if r['status'] == 'ERROR')

        click.echo(f"📈 状态统计: ✅{ok_count} ⚠️{warning_count} ❌{error_count}")

    except Exception as e:
        click.echo(f"服务器状态检查失败: {e}")


@click.command()
@with_appcontext
def restart_services():
    """重启服务器组件"""
    import subprocess

    services = ['nginx', 'supervisor', 'mysql']

    click.echo("🔄 准备重启服务组件...")

    for service in services:
        try:
            click.echo(f"重启 {service}...")
            result = subprocess.run(['sudo', 'systemctl', 'restart', service],
                                    capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                click.echo(f"✅ {service} 重启成功")
            else:
                click.echo(f"❌ {service} 重启失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            click.echo(f"⏰ {service} 重启超时")
        except Exception as e:
            click.echo(f"❌ {service} 重启异常: {e}")

    # 重启应用进程
    try:
        click.echo("重启应用进程...")
        subprocess.run(['sudo', 'supervisorctl', 'restart', 'mixuebi:*'],
                       capture_output=True, text=True, timeout=30)
        click.echo("✅ 应用进程重启完成")
    except Exception as e:
        click.echo(f"❌ 应用进程重启失败: {e}")


@click.command()
@with_appcontext
def logs_tail():
    """实时查看应用日志"""
    import subprocess
    import os

    log_files = [
        '/home/ubuntu/mixuebi/logs/supervisor.log',
        '/var/log/nginx/mixuebi_error.log',
        '/var/log/nginx/mixuebi_access.log',
        '/home/ubuntu/mixuebi/app.log'
    ]

    click.echo("📜 实时查看系统日志 (Ctrl+C 退出)...")
    click.echo("=" * 60)

    for log_file in log_files:
        if os.path.exists(log_file):
            click.echo(f"📁 {log_file}")
        else:
            click.echo(f"❌ {log_file} (文件不存在)")

    click.echo("=" * 60)

    try:
        # 使用tail -f 查看最新日志
        existing_logs = [f for f in log_files if os.path.exists(f)]
        if existing_logs:
            subprocess.run(['tail', '-f'] + existing_logs)
        else:
            click.echo("❌ 没有找到可用的日志文件")
    except KeyboardInterrupt:
        click.echo("\n👋 退出日志查看")
    except Exception as e:
        click.echo(f"❌ 日志查看失败: {e}")


@click.command()
@with_appcontext
def performance_report():
    """生成性能报告"""
    try:
        import psutil
        from app.utils.monitor import system_monitor

        click.echo("📊 生成系统性能报告...")
        click.echo("=" * 60)

        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        click.echo(f"🖥️  CPU: {cpu_percent:.1f}% ({cpu_count} 核心)")

        # 内存信息
        memory = psutil.virtual_memory()
        click.echo(
            f"💾 内存: {memory.percent:.1f}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)")

        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        click.echo(
            f"💿 磁盘: {disk_percent:.1f}% ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)")

        # 网络连接
        connections = len(psutil.net_connections())
        click.echo(f"🌐 网络连接: {connections} 个")

        # 进程信息
        processes = len(psutil.pids())
        click.echo(f"⚙️  运行进程: {processes} 个")

        # 系统负载
        load_avg = psutil.getloadavg()
        click.echo(f"📈 系统负载: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")

        # 获取最近错误率
        error_rate = system_monitor.get_error_rate(minutes=60)
        click.echo(f"🚨 最近1小时错误率: {error_rate:.2f} 错误/分钟")

        # 最新告警
        from app.models.system_monitor import SystemAlert, AlertStatus
        open_alerts = SystemAlert.query.filter_by(status=AlertStatus.OPEN).count()
        click.echo(f"⚠️  未处理告警: {open_alerts} 个")

        click.echo("=" * 60)
        click.echo("✅ 性能报告生成完成")

    except Exception as e:
        click.echo(f"❌ 性能报告生成失败: {e}")


@click.command()
@with_appcontext
def create_test_logs():
    """创建测试日志文件（用于开发环境测试）"""
    import os

    try:
        # 创建logs目录
        logs_dir = os.path.join(current_app.root_path, '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # 创建测试的Nginx访问日志
        nginx_access_log = os.path.join(logs_dir, 'nginx_access.log')
        with open(nginx_access_log, 'w', encoding='utf-8') as f:
            f.write("""127.0.0.1 - - [17/Aug/2025:21:30:15 +0800] "GET /monitor HTTP/1.1" 200 5432 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
127.0.0.1 - - [17/Aug/2025:21:30:16 +0800] "GET /monitor/api/system-status HTTP/1.1" 200 128 "http://localhost:5000/monitor" "Mozilla/5.0"
127.0.0.1 - - [17/Aug/2025:21:30:20 +0800] "GET /monitor/logfiles HTTP/1.1" 200 8765 "http://localhost:5000/monitor" "Mozilla/5.0"
127.0.0.1 - - [17/Aug/2025:21:31:05 +0800] "POST /monitor/api/alerts/1/acknowledge HTTP/1.1" 200 45 "http://localhost:5000/monitor/alerts" "Mozilla/5.0"
""")

        # 创建测试的Nginx错误日志
        nginx_error_log = os.path.join(logs_dir, 'nginx_error.log')
        with open(nginx_error_log, 'w', encoding='utf-8') as f:
            f.write("""2025/08/17 21:25:30 [error] 1234#0: *1 connect() failed (111: Connection refused) while connecting to upstream
2025/08/17 21:26:15 [warn] 1234#0: *2 upstream server temporarily disabled while connecting to upstream
2025/08/17 21:27:22 [error] 1234#0: *3 FastCGI sent in stderr: "PHP message: PHP Fatal error: Uncaught Error"
2025/08/17 21:28:10 [info] 1234#0: *4 client closed connection while waiting for request
""")

        # 创建测试的Supervisor日志
        supervisor_log = os.path.join(logs_dir, 'supervisor.log')
        with open(supervisor_log, 'w', encoding='utf-8') as f:
            f.write("""2025-08-17 21:20:15,123 INFO spawned: 'mixuebi' with pid 5678
2025-08-17 21:20:15,125 INFO success: mixuebi entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
2025-08-17 21:25:30,456 WARN received SIGTERM indicating exit request
2025-08-17 21:25:31,789 INFO stopped: mixuebi (exit status 0)
2025-08-17 21:25:32,012 INFO spawned: 'mixuebi' with pid 5890
2025-08-17 21:25:32,015 INFO success: mixuebi entered RUNNING state, process has stayed up for > than 1 seconds (startsecs)
2025-08-17 21:30:45,234 ERROR spawn err: can't find command 'mixuebi_celery'
""")

        # 创建测试的应用错误日志
        app_error_log = os.path.join(logs_dir, 'error.log')
        with open(app_error_log, 'w', encoding='utf-8') as f:
            f.write("""2025-08-17 21:25:15 ERROR [app.utils.notify:45] 邮件发送失败: {'': (550, b'Invalid User:')}
2025-08-17 21:26:20 WARNING [app.views.monitor_views:123] 磁盘空间不足: 5.2% 剩余
2025-08-17 21:27:30 ERROR [app.extensions:67] 数据库连接超时
2025-08-17 21:28:45 ERROR [app.models.user:89] 用户登录失败: 密码错误
2025-08-17 21:29:10 CRITICAL [app.utils.scheduler:156] 定时任务执行失败: 内存不足
""")

        click.echo("✅ 测试日志文件创建完成！")
        click.echo(f"📁 日志目录: {logs_dir}")
        click.echo("📋 创建的文件:")
        click.echo(f"  - nginx_access.log  (Nginx访问日志)")
        click.echo(f"  - nginx_error.log   (Nginx错误日志)")
        click.echo(f"  - supervisor.log    (Supervisor日志)")
        click.echo(f"  - error.log         (应用错误日志)")
        click.echo("\n🔗 访问 http://localhost:5000/monitor/logfiles 查看日志文件")

    except Exception as e:
        click.echo(f"❌ 创建测试日志文件失败: {e}")


def register_commands(app):
    app.cli.add_command(fake_data_command)
    app.cli.add_command(init_monitoring)
    app.cli.add_command(cleanup_monitoring_data)
    app.cli.add_command(test_monitoring)
    app.cli.add_command(server_status)
    app.cli.add_command(restart_services)
    app.cli.add_command(logs_tail)
    app.cli.add_command(performance_report)
    app.cli.add_command(create_test_logs)


# 兼容旧用法，提供init_app别名
init_app = register_commands
