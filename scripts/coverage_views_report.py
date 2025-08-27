# -*- coding: utf-8 -*-
"""
Usage:
    # 1) run tests with coverage data collected
    coverage erase && coverage run -m pytest -q
    # 2) run this reporter
    python scripts/coverage_views_report.py

It prints each app/views/*.py file with its missing line numbers.
If a file shows [] then it is 100% covered.
"""
import glob
import json
import os
import sys

try:
    from coverage import Coverage
except Exception as e:
    print("[ERROR] coverage is not installed:", e)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(__file__))
os.chdir(ROOT)

cov = Coverage()
try:
    cov.load()
except Exception as e:
    print("[ERROR] failed to load .coverage data:", e)
    print("Hint: run 'coverage run -m pytest -q' first.")
    sys.exit(2)

rows = []
for f in sorted(glob.glob('app/views/*.py')):
    try:
        fname, statements, excluded, missing, executed = cov.analysis2(f)
        rows.append({'file': f, 'missing': missing, 'count': len(missing)})
    except Exception as e:
        rows.append({'file': f, 'error': str(e)})

print(json.dumps(rows, ensure_ascii=False, indent=2))
