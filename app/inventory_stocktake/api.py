"""内部 JSON 接口（同域）。

需求确认：允许同域内部接口用于提升交互体验；禁止对外公开/跨域 REST API。
因此所有接口：
- 必须登录（login_required）
- 默认不启用 CORS
- 仅返回 JSON 给同站点页面使用
"""

from __future__ import annotations

from datetime import date

from flask import jsonify, request
from flask_login import current_user, login_required

from app.inventory_stocktake import inventory_stocktake_bp
from app.inventory_stocktake.services.material_query_service import search_materials
from app.inventory_stocktake.services.stocktake_service import reset, save_one
from app.inventory_stocktake.services.value_calc_service import UnitPriceMissingError, calc_values


@inventory_stocktake_bp.route("/api/value", methods=["GET"])
@login_required
def api_value_calc():
    """货值计算内部接口。

    Query:
      - store_id: 店铺ID
      - check_date: YYYY-MM-DD
    """

    store_id = request.args.get("store_id")
    check_date_str = request.args.get("check_date")

    if not store_id or not check_date_str:
        return jsonify({"ok": False, "message": "store_id 和 check_date 必填"}), 400

    try:
        d = date.fromisoformat(check_date_str)
    except Exception:
        return jsonify({"ok": False, "message": "check_date 格式必须为 YYYY-MM-DD"}), 400

    try:
        details, cat_sum, total = calc_values(store_id, d)
        return jsonify(
            {
                "ok": True,
                "data": {
                    "details": [
                        {
                            "material_code": r.material_code,
                            "material_name": r.material_name,
                            "category": r.category,
                            "remaining_case_qty": r.remaining_case_qty,
                            "remaining_group_qty": r.remaining_group_qty,
                            "price_per_case": str(r.price_per_case),
                            "price_per_group": str(r.price_per_group),
                            "value": str(r.value),
                        }
                        for r in details
                    ],
                    "category_sum": {k: str(v) for k, v in cat_sum.items()},
                    "total": str(total),
                },
            }
        )
    except UnitPriceMissingError as e:
        return jsonify({"ok": False, "message": str(e)}), 422


@inventory_stocktake_bp.route("/api/materials", methods=["GET"])
@login_required
def api_materials():
    """物料列表（分页/搜索）内部接口。"""

    q = request.args.get("q")
    page = request.args.get("page", 1)
    page_size = request.args.get("page_size", 50)

    items, total = search_materials(q=q, page=int(page), page_size=int(page_size))
    return jsonify(
        {
            "ok": True,
            "data": {
                "items": items,
                "total": total,
                "page": int(page),
                "page_size": int(page_size),
            },
        }
    )


@inventory_stocktake_bp.route("/api/stocktake/save", methods=["POST"])
@login_required
def api_stocktake_save_one():
    """保存单条盘点（含行级有效期至）。

    JSON:
      store_id, check_date(YYYY-MM-DD), material_code, material_name, spec_model,
      remaining_case_qty, remaining_group_qty, valid_until(YYYY-MM-DD optional)
    """

    payload = request.get_json(silent=True) or {}

    store_id = payload.get("store_id")
    check_date_str = payload.get("check_date")
    material_code = payload.get("material_code")
    material_name = payload.get("material_name")
    spec_model = payload.get("spec_model")
    remaining_case_qty = payload.get("remaining_case_qty")
    remaining_group_qty = payload.get("remaining_group_qty")
    valid_until_str = payload.get("valid_until")

    if not store_id or not check_date_str:
        return jsonify({"ok": False, "message": "store_id 和 check_date 必填"}), 400

    try:
        d = date.fromisoformat(check_date_str)
    except Exception:
        return jsonify({"ok": False, "message": "check_date 格式必须为 YYYY-MM-DD"}), 400

    valid_until = None
    if valid_until_str:
        try:
            valid_until = date.fromisoformat(valid_until_str)
        except Exception:
            return jsonify({"ok": False, "message": "valid_until 格式必须为 YYYY-MM-DD"}), 400

    try:
        res = save_one(
            store_id=store_id,
            check_date=d,
            operator=getattr(current_user, "username", None),
            material_code=material_code,
            material_name=material_name,
            spec_model=spec_model,
            remaining_case_qty=remaining_case_qty,
            remaining_group_qty=remaining_group_qty,
            valid_until=valid_until,
        )
        return jsonify({"ok": True, "message": res.message})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 400


@inventory_stocktake_bp.route("/api/stocktake/reset", methods=["POST"])
@login_required
def api_stocktake_reset():
    payload = request.get_json(silent=True) or {}
    store_id = payload.get("store_id")
    check_date_str = payload.get("check_date")
    if not store_id or not check_date_str:
        return jsonify({"ok": False, "message": "store_id 和 check_date 必填"}), 400
    try:
        d = date.fromisoformat(check_date_str)
    except Exception:
        return jsonify({"ok": False, "message": "check_date 格式必须为 YYYY-MM-DD"}), 400

    n = reset(store_id, d)
    return jsonify({"ok": True, "message": f"已清空 {n} 条"})
