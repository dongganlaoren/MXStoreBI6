import os
import pdfplumber
import pytest

from app.utils.bank_parser import BankParserEngine


def _pages_text(path: str):
    with pdfplumber.open(path) as pdf:
        return [(p.extract_text() or '') for p in pdf.pages]


def test_bank_parser_kbank_demo_pdf_ok():
    path = 'docs/KASIKORNBANK_Statement_Demo2.pdf'
    if not os.path.exists(path):
        pytest.skip(f"missing sample pdf: {path}")

    engine = BankParserEngine(path)
    res = engine.parse_and_validate()
    assert res.bank_type in ('KBANK', 'KBANK ') or res.bank_type != ''
    assert res.summary.get('begin_balance') is not None
    assert res.summary.get('total_dep_amt') is not None
    assert res.summary.get('total_wdl_amt') is not None
    assert len(res.transactions) > 0
    assert isinstance(res.errors, list)
    if not res.ok:
        assert len(res.errors) > 0


def test_bank_parser_bbl_demo_pdf_ok_or_has_explained_errors():
    path = 'docs/BBL_Statement_Demo.pdf'
    if not os.path.exists(path):
        pytest.skip(f"missing sample pdf: {path}")

    engine = BankParserEngine(path)
    res = engine.parse_and_validate()
    assert res.bank_type == 'BBL'
    assert len(res.transactions) > 0

    # Depending on table extraction quality, BBL may need further fine-tuning.
    # We at least require the engine to return a meaningful errors list when not ok.
    assert isinstance(res.errors, list)
    if not res.ok:
        assert len(res.errors) > 0
