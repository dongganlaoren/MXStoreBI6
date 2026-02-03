from __future__ import annotations

import os
import tempfile
from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.inventory_stocktake import inventory_stocktake_bp
from app.inventory_stocktake.forms import StocktakeFilterForm
from app.inventory_stocktake.services.material_service import upsert_materials
from app.inventory_stocktake.services.period_service import default_stocktake_date
from app.inventory_stocktake.utils.excel_parser import parse_material_template
from app.models.store import Store


@inventory_stocktake_bp.route("/")
@login_required
def index():
    """模块入口页：按需求最终会做盘点/统计导航；这里先给出最小可用入口。"""
    return render_template("inventory_stocktake/index.html")


@inventory_stocktake_bp.route("/material", methods=["GET", "POST"])
@login_required
def material_import():
    """物料信息模板导入维护页（仅导入，无导出）。"""

    summary = None
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename:
            flash("请选择要上传的Excel模板文件", "warning")
            return redirect(url_for("inventory_stocktake.material_import"))

        # 保存到临时文件，交给 openpyxl 读取
        suffix = os.path.splitext(f.filename)[1] or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        try:
            rows = parse_material_template(tmp_path)
            summary = upsert_materials(rows)
        except Exception as e:
            flash(str(e), "danger")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return render_template("inventory_stocktake/material.html", summary=summary)


@inventory_stocktake_bp.route("/stocktake", methods=["GET"])
@login_required
def stocktake_page():
    """库存盘点录入页（第一版占位）。

    需求口径：每月最后一天闭店后盘点，第二天录入系统。
    因此默认日期 = 上个月最后一天，但允许用户修改日期做补录。

    说明：盘点明细录入（物料列表、分页、保存）将通过同域内部接口增强交互，后续迭代完善。
    """

    form = StocktakeFilterForm()

    stores = Store.query.order_by(Store.store_id.asc()).all()
    form.store_id.choices = [(s.store_id, f"{s.store_id} - {s.store_name}") for s in stores]

    # 默认店铺：员工/店长取自己的 store_id；管理员取列表第一项
    default_store_id = None
    if hasattr(current_user, "store_id") and getattr(current_user, "store_id"):
        default_store_id = current_user.store_id
    elif stores:
        default_store_id = stores[0].store_id

    store_id = request.args.get("store_id") or default_store_id

    check_date_str = request.args.get("check_date")
    if check_date_str:
        try:
            d = date.fromisoformat(check_date_str)
        except Exception:
            d = default_stocktake_date()
            flash("check_date 参数格式错误，已使用默认盘点日期", "warning")
    else:
        d = default_stocktake_date()

    # 表单默认值
    if store_id:
        form.store_id.data = store_id
    form.check_date.data = d

    return render_template(
        "inventory_stocktake/stocktake.html",
        form=form,
        store_id=store_id,
        check_date=d,  # template will stringify to ISO
    )
