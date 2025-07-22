# app/commands.py
import click
from flask.cli import with_appcontext

from app.extensions import db
from app.utils.fake_data import (
    create_fake_daily_sales,
    create_fake_reimbursements,
    create_fake_stores,
    create_fake_users,
)


@click.command()
@with_appcontext
def init_db():
    """初始化数据库"""
    db.create_all()
    click.echo("Initialized the database.")


@click.command()
@with_appcontext
def create_fake_data():
    """创建测试数据"""
    create_fake_users()
    create_fake_stores()
    create_fake_daily_sales()
    create_fake_reimbursements()
    click.echo("Created fake data.")


def init_app(app):
    """初始化命令"""
    app.cli.add_command(init_db)
    app.cli.add_command(create_fake_data)
