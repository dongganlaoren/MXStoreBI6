from __future__ import annotations

import os
import tempfile
from datetime import date

from flask import flash, redirect, render_template, request, url_for, send_file, current_app
from flask_login import login_required
from sqlalchemy import distinct

from app.extensions import db
from app.inventory_stocktake import inventory_stocktake_bp
from app.inventory_stocktake.forms import StocktakeFilterForm
from app.inventory_stocktake.models import MXMaterialInfo
from app.inventory_stocktake.services.material_service import upsert_materials
from app.inventory_stocktake.services.period_service import default_stocktake_date
from app.inventory_stocktake.services.store_access_service import get_accessible_stores
from app.inventory_stocktake.utils.excel_parser import parse_material_template
from app.models.enums import RoleType
from app.utils.decorators import role_required


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
@role_required(RoleType.ADMIN.name)
def material_import():
    """产品信息维护页：

    - 支持下载固定模板
    - 支持 Excel 批量导入（新增/更新）
    - 支持对已有产品做基本字段维护（表格编辑）
    """

    # 获取去重类别列表供下拉框使用
    existing_categories = [r[0] for r in
                           db.session.query(distinct(MXMaterialInfo.category)).order_by(MXMaterialInfo.category).all()]
    if not existing_categories:
        # 提供一些默认值以防数据库完全为空
        existing_categories = ["食材类", "包材类", "耗材类"]

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

        try:
            m.per_group_qty = int(request.form.get("per_group_qty")) if (request.form.get(
                "per_group_qty") or "").strip() != "" else m.per_group_qty
        except Exception:
            flash("每件组数必须为整数", "warning")
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

        # 图片上传处理
        img_file = request.files.get("product_image_file")
        if img_file and img_file.filename:
            try:
                ext = os.path.splitext(img_file.filename)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                    raise ValueError("仅支持 jpg/png/gif 图片格式")

                # 使用物料编码命名，避免乱码和冲突
                new_filename = f"{m.material_code}{ext}"
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'materials')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)

                img_path = os.path.join(upload_dir, new_filename)
                img_file.save(img_path)

                # 存入数据库的是相对路径
                m.product_image = f"uploads/materials/{new_filename}"
            except Exception as e:
                flash(f"图片上传失败: {str(e)}", "warning")

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

    # 第一排序规则是物料类别，第二排序规则是物料编码
    materials = query.order_by(MXMaterialInfo.category.asc(), MXMaterialInfo.material_code.asc()).limit(300).all()

    return render_template("inventory_stocktake/material.html", summary=summary, materials=materials, q=q,
                           categories=existing_categories)


@inventory_stocktake_bp.route("/stocktake", methods=["GET"])
@login_required
def stocktake_page():
    """库存盘点录入（新版本）：

    - 默认绑定当前登录用户所属店铺（BRANCH_MANAGER/EMPLOYEE）
    - ADMIN/HEAD_MANAGER 可选择全部店铺
    - 选择盘点日期
    - 取消搜索，保留重置
    - 取消单行保存，改为统一保存；支持草稿保存与正式提交
    """

    form = StocktakeFilterForm()

    stores, default_store_id, locked = get_accessible_stores()
    form.store_id.choices = [(s.store_id, f"{s.store_id} - {s.store_name}") for s in stores]

    store_id = request.args.get("store_id") or default_store_id
    if locked:
        store_id = default_store_id

    if not store_id:
        flash("当前用户未绑定店铺，无法进行盘点录入", "warning")

    check_date_str = request.args.get("check_date")
    if check_date_str:
        try:
            d = date.fromisoformat(check_date_str)
        except Exception:
            d = default_stocktake_date()
            flash("check_date 参数格式错误，已使用默认盘点日期", "warning")
    else:
        d = default_stocktake_date()

    if store_id:
        form.store_id.data = store_id
    form.check_date.data = d

    return render_template(
        "inventory_stocktake/stocktake_entry.html",
        form=form,
        store_id=store_id,
        check_date=d,
        store_locked=locked,
    )


@inventory_stocktake_bp.route("/records", methods=["GET"])
@login_required
def stocktake_records_page():
    """盘点记录：查询各店铺每次盘点信息，并可计算库存价值（泰铢）。"""

    form = StocktakeFilterForm()
    stores, default_store_id, locked = get_accessible_stores()

    # 构建选项：管理员允许看见"全部店铺"
    choices = [(s.store_id, f"{s.store_id} - {s.store_name}") for s in stores]
    if not locked:
        # 为管理员添加空选项，用于"全部"
        choices.insert(0, ("", "全部店铺"))
    form.store_id.choices = choices

    store_id = request.args.get("store_id")

    if locked:
        # 锁定状态：必须是 default_store_id
        store_id = default_store_id
    else:
        # 非锁定状态：如果没有指定参数，则默认为空（即全部）
        # 原逻辑：or default_store_id 会强制选中第一个
        if store_id is None:
            store_id = ""

    # records页日期用于筛选（可空）
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if start_date_str:
        try:
            form.start_date.data = date.fromisoformat(start_date_str)
        except Exception:
            pass
    if end_date_str:
        try:
            form.end_date.data = date.fromisoformat(end_date_str)
        except Exception:
            pass

    if store_id:
        form.store_id.data = store_id

    return render_template(
        "inventory_stocktake/records.html",
        form=form,
        store_id=store_id,
        start_date=form.start_date.data,
        end_date=form.end_date.data,
        store_locked=locked,
    )
