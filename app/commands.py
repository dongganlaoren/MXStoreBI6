# app/commands.py
import click
from flask import current_app
from flask.cli import with_appcontext

from app.utils.fake_data import generate_fake_data, clean_daily_sales_duplicates


@click.command("fake-data")
@with_appcontext
def fake_data_command():
    """
    生成测试数据，并清理重复归档日报。
    """
    click.echo("开始生成测试数据...")
    generate_fake_data()
    click.echo("测试数据生成完毕！")
    click.echo("开始清理重复归档日报...")
    clean_daily_sales_duplicates()
    click.echo("重复归档日报清理完毕！")


def register_commands(app):
    app.cli.add_command(fake_data_command)


# 兼容旧用法，提供init_app别名
init_app = register_commands