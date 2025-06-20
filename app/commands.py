# app/commands.py
import click
from flask.cli import with_appcontext

from app.utils.fake_data import generate_fake_data  # 直接导入函数


@click.command("fake-data")
@with_appcontext
def fake_data():
    """Generate fake data."""
    generate_fake_data()  # 不传参数
    print("✅ 已完成测试数据的生成，请检查数据库！")

def init_app(app):
    app.cli.add_command(fake_data)
