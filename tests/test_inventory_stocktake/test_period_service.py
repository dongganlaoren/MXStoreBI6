from __future__ import annotations

from datetime import date

from app.inventory_stocktake.services.period_service import default_stocktake_date


def test_default_stocktake_date_is_last_day_of_previous_month():
    """默认盘点日期：上个月最后一天。

    业务说明：盘点一般在每月最后一天闭店后进行，次日录入系统。
    但盘点日期不做强制锁定（用户可手动选择其他日期补录）。
    """

    assert default_stocktake_date(date(2026, 2, 1)) == date(2026, 1, 31)
    assert default_stocktake_date(date(2026, 3, 1)) == date(2026, 2, 28)
    # leap year
    assert default_stocktake_date(date(2024, 3, 1)) == date(2024, 2, 29)


def test_default_stocktake_date_for_middle_of_month():
    # 即使不是月初进入，默认仍指向上个月最后一天，便于补录
    assert default_stocktake_date(date(2026, 3, 15)) == date(2026, 2, 28)
