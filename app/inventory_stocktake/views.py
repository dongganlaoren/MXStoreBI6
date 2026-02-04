from __future__ import annotations

import os
import tempfile
from datetime import date

from flask import flash, redirect, render_template, request, url_for, send_file, current_app
from flask_login import current_user, login_required

from app.extensions import db
from app.inventory_stocktake import inventory_stocktake_bp
from app.inventory_stocktake.forms import StocktakeFilterForm
from app.inventory_stocktake.models import MXMaterialInfo
from app.inventory_stocktake.services.material_service import upsert_materials
from app.inventory_stocktake.services.period_service import default_stocktake_date
from app.inventory_stocktake.utils.excel_parser import parse_material_template
from app.models.store import Store


@inventory_stocktake_bp.route("/")
@login_required
def index():
    """模块入口页：按需求最终会做盘点/统计导航；这里先给出最小可用入口。"""
    return render_template("inventory_stocktake/index.html")


@inventory_stocktake_bp.route("/material/template", methods=["GET"])
@login_required
def material_template_download():
    """下载固定格式的 inventory_stocktake_template.xlsx（禁止随意改格式）。"""

    # 固定从仓库 templates/ 下发放
    root_path = current_app.root_path
    # current_app.root_path = app/; template file is at repo_root/templates/
    repo_root = os.path.abspath(os.path.join(root_path, os.pardir))
    fp = os.path.join(repo_root, "templates", "inventory_stocktake_template.xlsx")
    return send_file(fp, as_attachment=True, download_name="inventory_stocktake_template.xlsx")


@inventory_stocktake_bp.route("/material", methods=["GET", "POST"])
@login_required
def material_import():
    """产品信息维护页：

    - 支持下载固定模板
    - 支持 Excel 批量导入（新增/更新）
    - 支持对已有产品做基本字段维护（表格编辑）
    """

    summary = None

    # 1) 处理“单条维护”提交
    if request.method == "POST" and (request.form.get("action") == "update_one"):
        code = request.form.get("material_code")
        if not code:
            flash("物料编码不能为空", "warning")
            return redirect(url_for("inventory_stocktake.material_import"))

        m = MXMaterialInfo.query.filter_by(material_code=code).first()
        if not m:
            flash("物料不存在", "danger")
            return redirect(url_for("inventory_stocktake.material_import"))

        # 允许维护的字段（基本信息）
        m.cn_name = (request.form.get("cn_name") or "").strip() or m.cn_name
        m.th_name = (request.form.get("th_name") or "").strip() or None
        m.spec_model = (request.form.get("spec_model") or "").strip() or m.spec_model
        m.category = (request.form.get("category") or "").strip() or m.category
        m.status = (request.form.get("status") or "").strip() or m.status
        m.remark = (request.form.get("remark") or "").strip() or None
        try:
            m.safety_stock = int(request.form.get("safety_stock")) if (request.form.get(
                "safety_stock") or "").strip() != "" else None
        except Exception:
            flash("安全库存必须为整数或留空", "warning")
            return redirect(url_for("inventory_stocktake.material_import"))

        # 单价允许为空；如果填写则校验为数字
        def _parse_decimal(name: str):
            v = (request.form.get(name) or "").strip()
            if v == "":
                return None
            try:
                return float(v)
            except Exception:
                raise ValueError(f"{name} 必须为数字或留空")

        try:
            m.price_per_case = _parse_decimal("price_per_case")
            m.price_per_group = _parse_decimal("price_per_group")
        except ValueError as e:
            flash(str(e), "warning")
            return redirect(url_for("inventory_stocktake.material_import"))

        db.session.commit()
        flash("保存成功", "success")
        return redirect(url_for("inventory_stocktake.material_import"))

    # 2) 处理 Excel 导入
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
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
        elif request.method == "POST":
            # 没有文件也不是 update_one
            flash("请选择要上传的Excel文件，或使用下方表格直接维护", "warning")

    # 3) 展示已有产品列表
    q = (request.args.get("q") or "").strip()
    query = MXMaterialInfo.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (MXMaterialInfo.material_code.like(like)) |
            (MXMaterialInfo.cn_name.like(like)) |
            (MXMaterialInfo.category.like(like))
        )

    materials = query.order_by(MXMaterialInfo.category.asc(), MXMaterialInfo.material_code.asc()).limit(300).all()

    return render_template("inventory_stocktake/material.html", summary=summary, materials=materials, q=q)


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
