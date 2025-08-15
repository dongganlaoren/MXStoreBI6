# app/utils/notify.py
from flask import current_app
from flask_mail import Message

from app.extensions import mail


def send_notify_mail(subject, recipients, body, html=None):
    """
    发送系统通知邮件（同步测试版）
    :param subject: 邮件主题
    :param recipients: 收件人列表（如：["xxx@163.com"]）
    :param body: 邮件正文（纯文本）
    :param html: 邮件正文（HTML，可选）
    :return: True/False
    """
    try:
        msg = Message(subject=subject,
                      recipients=recipients,
                      body=body,
                      html=html)
        # 同步发送邮件（不使用线程）
        mail.send(msg)
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
