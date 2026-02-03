from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from app.inventory_stocktake.models import MXInventoryCheck


@dataclass
class ExpiryReminderItem:
    id: int
    store_id: str
    check_date: date
    material_code: str
    material_name: str
    valid_until: date
    remind_on: date


def list_items_to_remind(today: Optional[date] = None, days_before: int = 30) -> List[ExpiryReminderItem]:
    """列出需要提醒的记录：有效期至不为空，且 (valid_until - days_before) <= today <= valid_until。

    需求：到期前 1 个月提醒。这里用 days_before=30 近似 1 个月。
    后续如要按自然月（如 2026-03-31 -> 2026-02-28）可再升级。
    """

    if today is None:
        today = date.today()

    start = today
    # 找到 valid_until 在 [today, today+days_before] 的项目，也就意味着“距离到期 <= days_before”
    end = today + timedelta(days=days_before)

    q = (
        MXInventoryCheck.query
        .filter(MXInventoryCheck.valid_until.isnot(None))
        .filter(MXInventoryCheck.valid_until >= start)
        .filter(MXInventoryCheck.valid_until <= end)
        .order_by(MXInventoryCheck.valid_until.asc())
    )

    items: List[ExpiryReminderItem] = []
    for r in q.all():
        items.append(
            ExpiryReminderItem(
                id=r.id,
                store_id=r.store_id,
                check_date=r.check_date,
                material_code=r.material_code,
                material_name=r.material_name,
                valid_until=r.valid_until,
                remind_on=r.valid_until - timedelta(days=days_before),
            )
        )

    return items
