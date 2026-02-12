import os

import pytest

from app.utils.bank_parser import BankParserEngine


@pytest.mark.slow
@pytest.mark.parametrize(
    "path,password,expected_bank",
    [
        ("docs/KASIKORNBANK_Statement_big_Demo.pdf", None, "KBANK"),
        ("docs/BBL_big_Demo.PDF", "15041990", "BBL"),
    ],
)
def test_large_pdfs_parse_transactions_and_no_summary_zero_misleading(path, password, expected_bank):
    if not os.path.exists(path):
        pytest.skip(f"missing sample pdf: {path}")

    engine = BankParserEngine(path, password=password)
    res = engine.parse_and_validate()

    assert res.bank_type == expected_bank
    assert len(res.transactions) > 0

    # If summary totals are missing, they must be None rather than 0 to avoid false validation failures.
    if expected_bank == "KBANK":
        assert res.summary.get("total_dep_amt") is None or res.summary.get("total_dep_amt") != 0
        assert res.summary.get("total_wdl_amt") is None or res.summary.get("total_wdl_amt") != 0
    if expected_bank == "BBL":
        assert res.summary.get("total_dep_amt") is None or res.summary.get("total_dep_amt") != 0
        assert res.summary.get("total_wdl_amt") is None or res.summary.get("total_wdl_amt") != 0
