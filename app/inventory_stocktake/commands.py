from __future__ import annotations

from flask import current_app

from app.inventory_stocktake.services.expiry_email_service import send_expiry_warning_emails
from app.inventory_stocktake.services.expiry_reminder_service import list_items_to_remind


def register_inventory_stocktake_commands(app):
    @app.cli.command("inventory-stocktake-remind")
    def inventory_stocktake_remind():
        """打印有效期临近的提醒列表（可供 crontab/apscheduler 调用）。"""

        with app.app_context():
            items = list_items_to_remind()
            if not items:
                current_app.logger.info("[inventory-stocktake] no expiry reminders")
                print("no expiry reminders")
                return

            for it in items:
                msg = (
                    "[inventory-stocktake] store={} check_date={} material={} {} valid_until={}".format(
                        it.store_id,
                        it.check_date,
                        it.material_code,
                        it.material_name,
                        it.valid_until,
                    )
                )
                current_app.logger.warning(msg)
                print(msg)

    @app.cli.command("inventory-stocktake-expiry-email")
    def inventory_stocktake_expiry_email():
        """发送临期提醒邮件（管理员 + 对应店长）。

        建议每日运行一次。
        """

        with app.app_context():
            stats = send_expiry_warning_emails(async_send=False)
            current_app.logger.warning("[inventory-stocktake] expiry email stats=%s", stats)
            print(stats)
