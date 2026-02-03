# app/commands.py

import click
from flask.cli import with_appcontext


@click.command("fake-data")
@with_appcontext
def fake_data_command():
    """
    生成测试数据，并清理重复归档日报。
    """
    # 惰性导入以避免在应用初始化时引入测试数据模块，防止循环依赖
    from app.utils.fake_data import generate_fake_data
    click.echo("开始生成测试数据...")
    generate_fake_data()
    click.echo("测试数据生成完毕！")


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


def register_commands(app):
    app.cli.add_command(fake_data_command)
    app.cli.add_command(restart_services)
    app.cli.add_command(logs_tail)


# 兼容旧用法，提供init_app别名
init_app = register_commands


def init_app(app):
    """Register commands."""
    register_commands(app)
    try:
        from app.inventory_stocktake.commands import register_inventory_stocktake_commands
        register_inventory_stocktake_commands(app)
    except Exception:
        # 避免命令注册影响主应用启动
        pass
