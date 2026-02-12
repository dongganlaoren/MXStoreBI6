"""CG bank statement parser smoke runner.

Writes results to a JSON file (so you don't rely on terminal stdout).

Usage:
    python scripts/cg_bank_parser_smoke.py docs/KASIKORNBANK_Statement_big_Demo.pdf
"""

from __future__ import annotations

import json
import os
import sys
import time

# Ensure project root is on sys.path so `import app.*` works no matter where we run from.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.utils.bank_parser import BankParserEngine


def _to_jsonable(obj):
    if obj is None:
        return None
    # Decimal -> str to preserve exact value
    try:
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return str(obj)
    except Exception:
        pass
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/cg_bank_parser_smoke.py <pdf_path> [password]")
        return 2

    pdf_path = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) >= 3 else None

    start = time.time()
    r = BankParserEngine(pdf_path, password=password).parse_and_validate()
    elapsed = time.time() - start

    out = {
        "pdf": pdf_path,
        "elapsed_sec": elapsed,
        "ok": r.ok,
        "bank_type": r.bank_type,
        "summary": _to_jsonable(r.summary or {}),
        "transactions_count": len(r.transactions or []),
        "errors": r.errors,
        "sample_transactions": _to_jsonable((r.transactions or [])[:5]),
    }

    out_path = os.path.abspath("tmp_bank_parser_smoke.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
