# app/commands.py
import click
from flask.cli import with_appcontext

from app.utils.fake_data import generate_fake_data  # 直接导入函数


@click.command("fake-data")
@with_appcontext
def fake_data():
    """
    生成测试数据，并根据结果给出准确的提示。
    """
    # 【核心修改 1】: 调用函数，并用一个变量来接收它的返回值
    print("--- 开始执行测试数据生成任务 ---")
    success = generate_fake_data()

    # 【核心修改 2】: 检查返回值，并打印相应的最终消息
    if success:
        print("✅✅✅ 任务成功: 所有测试数据已成功生成，请检查数据库！")
    else:
        print("❌❌❌ 任务失败: 数据生成过程中发生错误，请检查上方的错误日志。")

def init_app(app):
    app.cli.add_command(fake_data)