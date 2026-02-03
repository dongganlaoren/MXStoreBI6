"""Print SQLAlchemy metadata tables for drift/migration checks.

Usage:
  .venv/bin/python tools/print_model_tables.py

This script loads the Flask app (TestingConfig) and prints:
- all tables declared in db.metadata
- for each table: columns and (basic) foreign keys

It is intentionally read-only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    # Make sure repo root is importable (so `import run` works).
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Ensure app can boot without requiring production env.
    os.environ.setdefault("FLASK_ENV", "testing")

    # TestingConfig uses sqlite:///:memory: by default; that's fine because we only
    # inspect models/metadata, not the live DB.
    from run import app  # noqa: F401
    from app.extensions import db

    tables = sorted(db.metadata.tables.values(), key=lambda t: t.name)

    print(f"Total tables in model metadata: {len(tables)}")
    for t in tables:
        print(f"\n== {t.name} ==")
        for c in t.columns:
            col = f"{c.name} {c.type}"
            if c.primary_key:
                col += " PK"
            if not c.nullable:
                col += " NOT NULL"
            if c.foreign_keys:
                targets = ",".join(sorted(str(fk.column) for fk in c.foreign_keys))
                col += f" FK->{targets}"
            print(col)


if __name__ == "__main__":
    main()
