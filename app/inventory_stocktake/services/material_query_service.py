from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import or_

from app.inventory_stocktake.models import MXMaterialInfo


def search_materials(*, q: str | None, page: int = 1, page_size: int = 50) -> Tuple[List[dict], int]:
    """同域内部查询：物料搜索 + 分页。

    返回 items 为 dict 列表，便于直接 jsonify。
    """

    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 200)

    query = MXMaterialInfo.query

    if q:
        s = q.strip()
        if s:
            like = "%{}%".format(s)
            query = query.filter(
                or_(
                    MXMaterialInfo.material_code.like(like),
                    MXMaterialInfo.cn_name.like(like),
                    MXMaterialInfo.spec_model.like(like),
                    MXMaterialInfo.category.like(like),
                )
            )

    total = query.count()
    rows = (
        query.order_by(MXMaterialInfo.material_code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return (
        [
            {
                "material_code": r.material_code,
                "cn_name": r.cn_name,
                "th_name": r.th_name,
                "spec_model": r.spec_model,
                "category": r.category,
            }
            for r in rows
        ],
        total,
    )
