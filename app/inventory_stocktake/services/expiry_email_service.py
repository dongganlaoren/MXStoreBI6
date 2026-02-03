from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Sequence

from flask import current_app

from app.inventory_stocktake.services.expiry_reminder_service import ExpiryReminderItem, list_items_to_remind
from app.models.enums import RoleType
from app.models.user import User
from app.utils.notify import send_notify_mail


def _get_admin_emails() -> List[str]:
    admins = User.query.filter(User.role == RoleType.ADMIN).all()
    return [u.email for u in admins if u.email]


def _get_store_manager_emails(store_id: str) -> List[str]:
    """获取该店铺负责人的邮箱。

    规则（可调整）：
    - role=BRANCH_MANAGER 且 store_id 匹配
    - 或者 is_primary_contact=True 且 store_id 匹配（作为兜底）
    """

    qs = User.query.filter(User.store_id == store_id).all()
    emails = []
    for u in qs:
        if not u.email:
            continue
        if u.role == RoleType.BRANCH_MANAGER or getattr(u, "is_primary_contact", False):
            emails.append(u.email)

    # 去重保持顺序
    seen = set()
    out = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def _render_subject(today: date) -> str:
    return "[库存盘点] 物料有效期临近提醒（{}）".format(today.isoformat())


def _render_body(today: date, store_id: str, items: Sequence[ExpiryReminderItem], days_before: int) -> str:
    lines = []
    lines.append("库存盘点 - 物料有效期临近提醒")
    lines.append("日期：{}".format(today.isoformat()))
    lines.append("店铺：{}".format(store_id))
    lines.append("规则：距离有效期<= {} 天触发提醒".format(days_before))
    lines.append("")
    lines.append("明细：")
    for it in items:
        lines.append(
            "- 物料：{} {} | 盘点日期：{} | 有效期至：{}".format(
                it.material_code,
                it.material_name,
                it.check_date.isoformat(),
                it.valid_until.isoformat(),
            )
        )
    lines.append("")
    lines.append("请及时处理临期物料（使用/报损/调拨等），并在系统中更新盘点数据。")
    return "\n".join(lines)


def send_expiry_warning_emails(
        *, today: Optional[date] = None, days_before: int = 30, async_send: bool = True
) -> Dict[str, int]:
    """发送临期提醒邮件给管理员 + 相应店长。

    返回统计：{"stores": x, "emails_sent": y, "items": z}
    """

    if today is None:
        today = date.today()

    items = list_items_to_remind(today=today, days_before=days_before)
    if not items:
        current_app.logger.info("[inventory-stocktake] expiry email: no items")
        return {"stores": 0, "emails_sent": 0, "items": 0}

    by_store = {}
    for it in items:
        by_store.setdefault(it.store_id, []).append(it)

    admin_emails = _get_admin_emails()

    emails_sent = 0
    for store_id, store_items in by_store.items():
        manager_emails = _get_store_manager_emails(store_id)
        recipients = []
        recipients.extend(admin_emails)
        recipients.extend(manager_emails)

        # 去重
        seen = set()
        recipients2 = []
        for r in recipients:
            if r and r not in seen:
                seen.add(r)
                recipients2.append(r)

        if not recipients2:
            current_app.logger.info("[inventory-stocktake] expiry email: skip store=%s no recipients", store_id)
            continue

        subject = _render_subject(today)
        body = _render_body(today, store_id, store_items, days_before)

        ok = send_notify_mail(subject, recipients2, body, async_send=async_send)
        if ok:
            emails_sent += 1

    return {"stores": len(by_store), "emails_sent": emails_sent, "items": len(items)}
