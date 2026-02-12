# app/services/cg_bank_statement_service.py
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from flask import current_app


class CgPdfPasswordRequired(Exception):
    """PDF is encrypted and all default passwords fail."""


@dataclass
class CgStatementSummary:
    opening_balance: float
    closing_balance: float
    credit_count: int
    credit_total: float
    debit_count: int
    debit_total: float
    currency: Optional[str] = None


@dataclass
class CgTxnRow:
    txn_date: str
    txn_time: Optional[str]
    description: str
    credit: float
    debit: float
    balance: float


@dataclass
class CgValidationLayerResult:
    ok: bool
    message: str
    expected: Optional[float] = None
    actual: Optional[float] = None
    diff: Optional[float] = None
    first_bad_index: Optional[int] = None


@dataclass
class CgValidationResult:
    ok: bool
    layer1: CgValidationLayerResult
    layer2: CgValidationLayerResult
    layer3: CgValidationLayerResult


def cg_md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def cg_default_passwords() -> List[str]:
    raw = os.environ.get('BANK_STATEMENT_PASSWORD') or ''
    return [p.strip() for p in raw.split(',') if p.strip()]


_amount_re = re.compile(r"-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?")


def _parse_amount_token(s: str) -> float:
    return float(s.replace(',', ''))


# NOTE: the parsing logic is implemented in app/utils/bank_parser.py.
# This service keeps backward-compatible helpers for the cg views.

from decimal import Decimal

from app.utils.bank_parser import BankParserEngine


def cg_extract_pdf_pages_text(pdf_path: str, user_password: Optional[str] = None) -> Tuple[List[str], bool]:
    """Compatibility shim.

    The new parsing engine opens PDF internally (with password fallback), so this function
    now only reports whether the PDF *looks* encrypted (best-effort) and returns empty pages.

    We keep it because the view expects it, but the view will call the engine for real parsing.
    """

    # best-effort: treat presence of user_password as 'encrypted'
    return [""], bool(user_password)


def cg_parse_statement(bank_code: str, pages_text: List[str]):
    raise NotImplementedError('cg_parse_statement 已被 BankParserEngine 替代，请在视图层直接调用引擎')


def _dec_to_float(d: Decimal) -> float:
    try:
        return float(d)
    except Exception:
        return 0.0


def cg_run_engine(pdf_path: str, user_password: Optional[str] = None):
    """Run BankParserEngine and convert result to cg view-friendly dataclasses."""

    engine = BankParserEngine(pdf_path, password=user_password)
    res = engine.parse_and_validate()
    return res


def cg_validate_three_layers(summary: 'CgStatementSummary', txns: List['CgTxnRow']) -> 'CgValidationResult':
    # Layer 1
    sum_credit = round(sum(r.credit for r in txns), 2)
    sum_debit = round(sum(r.debit for r in txns), 2)
    l1_ok = (
            round(summary.credit_total, 2) == sum_credit and
            round(summary.debit_total, 2) == sum_debit and
            (summary.credit_count + summary.debit_count == len(txns))
    )
    layer1 = CgValidationLayerResult(
        ok=l1_ok,
        message='汇总逻辑校验通过' if l1_ok else '汇总逻辑校验失败',
        expected=None,
        actual=None,
        diff=None,
    )

    # Layer 2
    first_bad = None
    for i in range(1, len(txns)):
        prev = txns[i - 1]
        cur = txns[i]
        expected_bal = round(prev.balance + cur.credit - cur.debit, 2)
        if round(cur.balance, 2) != expected_bal:
            first_bad = i
            break
    l2_ok = first_bad is None
    layer2 = CgValidationLayerResult(
        ok=l2_ok,
        message='余额连续性校验通过' if l2_ok else '余额连续性校验失败',
        first_bad_index=first_bad,
    )

    # Layer 3
    expected_close = round(summary.opening_balance + sum_credit - sum_debit, 2)
    actual_close = round(summary.closing_balance, 2)
    l3_ok = expected_close == actual_close
    layer3 = CgValidationLayerResult(
        ok=l3_ok,
        message='期初期末校验通过' if l3_ok else '期初期末校验失败',
        expected=expected_close,
        actual=actual_close,
        diff=round(actual_close - expected_close, 2),
    )

    ok = layer1.ok and layer2.ok and layer3.ok
    return CgValidationResult(ok=ok, layer1=layer1, layer2=layer2, layer3=layer3)


def cg_bsave_path(filename: str, file_hash: str) -> Tuple[str, str]:
    base_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    rel_dir = os.path.join('cg', 'bank_statement')
    abs_dir = os.path.join(base_folder, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    ext = os.path.splitext(filename)[1].lower() or '.pdf'
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.splitext(filename)[0])
    final_name = "{}_{}{}".format(safe_name, file_hash[:12], ext)
    abs_path = os.path.join(abs_dir, final_name)

    prefix = 'app/static/'
    if base_folder.startswith(prefix):
        rel_path = os.path.join(base_folder[len(prefix):], rel_dir, final_name)
    else:
        rel_path = os.path.join(base_folder, rel_dir, final_name)

    return abs_path, rel_path.replace('\\', '/')
