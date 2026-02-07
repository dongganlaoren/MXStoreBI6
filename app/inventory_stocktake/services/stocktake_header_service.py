from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.inventory_stocktake.models import MXInventoryCheck, MXInventoryDraft, MXMaterialInfo, MXStocktakeHeader
from app.inventory_stocktake.services.store_access_service import get_accessible_stores
from app.inventory_stocktake.services.value_calc_service import calc_values
from app.inventory_stocktake.utils.validators import ValidationError, parse_non_negative_int, require_non_empty


@dataclass
class DraftSaveResult:
    saved: int
    failed: int
    message: str


@dataclass
class CommitResult:
    header_id: int
    message: str


@dataclass
class CommitWithItemsResult(CommitResult):
    committed: int


def _ensure_store_access(store_id: str) -> None:
    _, default_store_id, locked = get_accessible_stores()
    if locked and default_store_id and store_id != default_store_id:
        raise ValidationError("无权限访问该店铺")


def get_or_create_header(*, store_id: str, check_date: date, operator: Optional[str]) -> MXStocktakeHeader:
    _ensure_store_access(store_id)

    header = MXStocktakeHeader.query.filter_by(store_id=store_id, check_date=check_date).first()
    if header is None:
        header = MXStocktakeHeader(
            store_id=store_id,
            check_date=check_date,
            status="DRAFT",
            created_by=operator,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(header)
        try:
            db.session.flush()  # get header.id
        except IntegrityError:
            # Concurrent create: unique(store_id, check_date) guarantees only one header.
            db.session.rollback()
            header = MXStocktakeHeader.query.filter_by(store_id=store_id, check_date=check_date).first()
            if header is None:
                raise
    return header


def _parse_iso_date(s: object) -> Optional[date]:
    if s is None:
        return None
    if isinstance(s, date):
        return s
    ss = str(s).strip()
    if not ss:
        return None
    try:
        return date.fromisoformat(ss)
    except Exception as e:
        raise ValidationError("有效期至格式必须为 YYYY-MM-DD") from e


def get_header_status(*, store_id: str, check_date: date) -> Optional[str]:
    """Return header status for a given store/date, or None if header not exists."""
    _ensure_store_access(store_id)
    h = MXStocktakeHeader.query.filter_by(store_id=store_id, check_date=check_date).first()
    return h.status if h else None


def save_draft_batch(*, store_id: str, check_date: date, operator: Optional[str], items: List[dict]) -> DraftSaveResult:
    """Unified save for draft: OVERWRITE all draft rows for the store.

    User Requirement: "New overwrites old".
    Impl:
    - Clear ALL existing drafts for this store (regardless of date/item).
    - Insert all valid items from the payload.
    - If payload is empty, store draft is effectively cleared.

    items: [{material_code, remaining_case_qty, remaining_group_qty, valid_until(optional)}]
    """

    store_id = require_non_empty(store_id, "店铺")
    header = get_or_create_header(store_id=store_id, check_date=check_date, operator=operator)

    if header.status != "DRAFT":
        raise ValidationError("该盘点已提交，无法继续保存草稿")

    # 1. Clear ALL drafts for this store (Complete Overwrite Strategy)
    clear_store_drafts(store_id=store_id)

    ok = 0
    fail = 0
    last_error: Optional[str] = None

    # 2. Bulk Insert
    for it in items:
        try:
            material_code = require_non_empty(it.get("material_code"), "物料编码")
            case_qty = parse_non_negative_int(it.get("remaining_case_qty"), "剩余整件数")
            group_qty = parse_non_negative_int(it.get("remaining_group_qty"), "剩余散件数")
            valid_until = _parse_iso_date(it.get("valid_until"))

            # Filter out empty rows (qty=0 and valid_until=None) to reset storage space
            if case_qty == 0 and group_qty == 0 and valid_until is None:
                continue

            mat = MXMaterialInfo.query.filter_by(material_code=material_code).first()
            if mat is None:
                raise ValidationError("物料编码不存在：%s" % material_code)

            # Direct Insert (no need to check existing, we just cleared them)
            d = MXInventoryDraft(
                store_id=store_id,
                check_date=check_date,
                material_code=material_code,
                material_name=mat.cn_name,
                spec_model=mat.spec_model,
                remaining_case_qty=case_qty,
                remaining_group_qty=group_qty,
                valid_until=valid_until,
                operator=operator,
                operated_at=datetime.utcnow(),
                header_id=header.id
            )
            db.session.add(d)
            ok += 1
        except OperationalError as e:
            msg = str(e)
            if "Unknown column" in msg and "header_id" in msg:
                raise ValidationError(
                    "数据库缺少字段 header_id：请先��行数据库迁移（flask db upgrade）后再保存草稿") from e
            last_error = msg
            fail += 1
        except Exception as e:
            last_error = str(e)
            fail += 1

    if ok == 0 and fail > 0:
        # If we failed on everything (and had items to try), rollback and error.
        # But if items was empty, ok=0 is success (cleared draft).
        if items:
            db.session.rollback()
            base = "保存失败：没有任何可保存的行"
            if last_error:
                base += f"（最后错误：{last_error}）"
            return DraftSaveResult(saved=0, failed=fail, message=base)

    db.session.commit()
    return DraftSaveResult(saved=ok, failed=fail, message=f"保存完成（覆盖保存{ok}条）")


def clear_store_drafts(*, store_id: str) -> int:
    """Delete all draft rows for a store (all dates).

    This is used after a successful commit to ensure no stale drafts remain for the store.
    Returns number of deleted rows.
    """

    store_id = require_non_empty(store_id, "店铺")
    return (
        MXInventoryDraft.query.filter(MXInventoryDraft.store_id == store_id)
        .delete(synchronize_session=False)
    )


def commit_stocktake_with_items(
        *,
        store_id: str,
        check_date: date,
        operator: Optional[str],
        items: List[dict],
) -> CommitWithItemsResult:
    """Commit stocktake directly from provided items without using draft table.

    items: [{material_code, remaining_case_qty, remaining_group_qty, valid_until(optional)}]

    - Upserts MXInventoryCheck rows
    - Marks header as COMMITTED
    - Clears drafts for the current store after committing
    """

    store_id = require_non_empty(store_id, "店铺")
    header = get_or_create_header(store_id=store_id, check_date=check_date, operator=operator)

    if header.status == "COMMITTED":
        return CommitWithItemsResult(header_id=header.id, committed=0, message="已提交，无需重复提交")

    if not items:
        raise ValidationError("没有盘点明细，无法提交")

    ok = 0
    for it in items:
        material_code = require_non_empty(it.get("material_code"), "物料编码")
        case_qty = parse_non_negative_int(it.get("remaining_case_qty"), "剩余整件数")
        group_qty = parse_non_negative_int(it.get("remaining_group_qty"), "剩余散件数")
        valid_until = _parse_iso_date(it.get("valid_until"))

        mat = MXMaterialInfo.query.filter_by(material_code=material_code).first()
        if mat is None:
            raise ValidationError("物料编码不存在：%s" % material_code)

        rec = MXInventoryCheck.query.filter_by(
            store_id=store_id,
            check_date=check_date,
            material_code=material_code,
        ).first()
        if rec is None:
            rec = MXInventoryCheck(
                store_id=store_id,
                check_date=check_date,
                material_code=material_code,
                material_name=mat.cn_name,
                spec_model=mat.spec_model,
            )
            db.session.add(rec)

        rec.remaining_case_qty = case_qty
        rec.remaining_group_qty = group_qty
        rec.valid_until = valid_until
        rec.operator = operator
        rec.operated_at = datetime.utcnow()
        rec.header_id = header.id
        ok += 1

    db.session.flush()
    try:
        _, _, total_val = calc_values(store_id, check_date)
        header.total_value_thb = total_val
    except Exception as e:
        raise ValidationError(str(e))

    header.status = "COMMITTED"
    header.committed_by = operator
    header.committed_at = datetime.utcnow()
    header.updated_at = datetime.utcnow()

    # 直提提交成功后：清空当前店铺所有草稿（所有日期），避免残留提示/串台
    clear_store_drafts(store_id=store_id)

    db.session.commit()
    return CommitWithItemsResult(header_id=header.id, committed=ok, message=f"提交成功（{ok}条）")


def commit_stocktake(*, store_id: str, check_date: date, operator: Optional[str]) -> CommitResult:
    store_id = require_non_empty(store_id, "店铺")
    header = get_or_create_header(store_id=store_id, check_date=check_date, operator=operator)

    if header.status == "COMMITTED":
        return CommitResult(header_id=header.id, message="已提交，无需重复提交")

    # must have at least one draft detail (store-scoped)
    drafts = MXInventoryDraft.query.filter_by(store_id=store_id).all()
    if not drafts:
        raise ValidationError("没有盘点明细，无法提交")

    # upsert committed details from draft
    for d in drafts:
        rec = MXInventoryCheck.query.filter_by(
            store_id=store_id,
            check_date=check_date,
            material_code=d.material_code,
        ).first()
        if rec is None:
            rec = MXInventoryCheck(
                store_id=store_id,
                check_date=check_date,
                material_code=d.material_code,
                material_name=d.material_name,
                spec_model=d.spec_model,
            )
            db.session.add(rec)

        rec.remaining_case_qty = d.remaining_case_qty
        rec.remaining_group_qty = d.remaining_group_qty
        rec.valid_until = d.valid_until
        rec.operator = operator
        rec.operated_at = datetime.utcnow()
        rec.header_id = header.id

    db.session.flush()
    try:
        _, _, total_val = calc_values(store_id, check_date)
        header.total_value_thb = total_val
    except Exception as e:
        raise ValidationError(str(e))

    header.status = "COMMITTED"
    header.committed_by = operator
    header.committed_at = datetime.utcnow()
    header.updated_at = datetime.utcnow()

    # 提交成功后：清空当前店铺所有草稿（所有日期），避免残留提示/串台
    clear_store_drafts(store_id=store_id)

    db.session.commit()
    return CommitResult(header_id=header.id, message="提交成功")


def list_stocktake_headers(*, store_id: Optional[str], status: Optional[str],
                           start_date: Optional[date] = None, end_date: Optional[date] = None,
                           page: int, page_size: int) -> Tuple[
    List[dict], int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 200)

    stores, default_store_id, locked = get_accessible_stores()

    q = MXStocktakeHeader.query
    if locked:
        if default_store_id:
            q = q.filter(MXStocktakeHeader.store_id == default_store_id)
        else:
            return [], 0
    else:
        if store_id:
            q = q.filter(MXStocktakeHeader.store_id == store_id)

    if status:
        q = q.filter(MXStocktakeHeader.status == status)
    else:
        q = q.filter(MXStocktakeHeader.status == "COMMITTED")

    if start_date:
        q = q.filter(MXStocktakeHeader.check_date >= start_date)
    if end_date:
        q = q.filter(MXStocktakeHeader.check_date <= end_date)

    total = q.count()
    rows = (
        q.order_by(MXStocktakeHeader.check_date.desc(), MXStocktakeHeader.store_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return (
        [
            {
                "id": r.id,
                "store_id": r.store_id,
                "check_date": r.check_date.isoformat(),
                "status": r.status,
                "total_value_thb": str(r.total_value_thb) if r.total_value_thb is not None else None,
                "created_by": r.created_by,
                "committed_by": r.committed_by,
                "committed_at": r.committed_at.isoformat() if r.committed_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
        total,
    )


def load_stocktake_details(*, store_id: str, check_date: date) -> List[dict]:
    """Load committed (locked) details for a store/date."""
    _ensure_store_access(store_id)

    rows = (
        db.session.query(MXInventoryCheck)
        .join(MXMaterialInfo, MXInventoryCheck.material_code == MXMaterialInfo.material_code)
        .filter(MXInventoryCheck.store_id == store_id, MXInventoryCheck.check_date == check_date)
        .order_by(MXMaterialInfo.category.asc(), MXMaterialInfo.material_code.asc())
        .all()
    )

    return [
        {
            "material_code": r.material_code,
            "remaining_case_qty": r.remaining_case_qty,
            "remaining_group_qty": r.remaining_group_qty,
            "valid_until": r.valid_until.isoformat() if r.valid_until else None,
        }
        for r in rows
    ]


def load_draft_details(*, store_id: str, check_date: date) -> List[dict]:
    """Load draft details for a store/date.

    User Req: "Same store, switching date should NOT prompt draft loading if draft belongs to another date."
    Impl:
    - Only return drafts that match (store_id, check_date).
    - If drafts exist for store_id but different date, return empty list (so no prompt).
    - If user saves on this new date, `save_draft_batch` will clear the old date's draft.
    """

    _ensure_store_access(store_id)

    try:
        rows = (
            db.session.query(MXInventoryDraft)
            .join(MXMaterialInfo, MXInventoryDraft.material_code == MXMaterialInfo.material_code)
            .filter(MXInventoryDraft.store_id == store_id, MXInventoryDraft.check_date == check_date)
            .order_by(MXMaterialInfo.category.asc(), MXMaterialInfo.material_code.asc())
            .all()
        )
    except OperationalError as e:
        msg = str(e)
        if "doesn't exist" in msg and "mx_inventory_draft" in msg:
            return []
        raise

    return [
        {
            "material_code": r.material_code,
            "remaining_case_qty": r.remaining_case_qty,
            "remaining_group_qty": r.remaining_group_qty,
            "valid_until": r.valid_until.isoformat() if r.valid_until else None,
        }
        for r in rows
    ]
