from __future__ import annotations

from datetime import date, timedelta


def default_stocktake_date(today: date | None = None) -> date:
    """默认盘点日期：取“上个月最后一天”。

    需求口径：每月最后一天闭店后盘点，第二天录入系统。
    因此当用户在“次日”进入系统，默认应指向上个月最后一天。

    例：
      - today=2026-02-01 -> 2026-01-31
      - today=2026-03-15 -> 2026-02-28

    若业务上允许补录更早月份，也应允许手工改日期；这里只给出默认值。
    """

    if today is None:
        today = date.today()

    first_of_this_month = date(today.year, today.month, 1)
    return first_of_this_month - timedelta(days=1)
