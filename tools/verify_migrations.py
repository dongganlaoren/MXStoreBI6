"""Verify that a fresh database can be migrated to Alembic head.

This script is meant for quick, repeatable migration validation.
It focuses on the test environment (SQLite), but it also helps catch drift
between SQLAlchemy models and Alembic migrations.

What it does:
1) Creates a fresh SQLite database file under instance/.
2) Runs `flask db upgrade` against that DB.
3) Imports the application models and compares the *set of table names*
   in the live database to those declared in SQLAlchemy metadata.

Usage:
  .venv/bin/python tools/verify_migrations.py

Exit codes:
- 0: success
- 1: migration failed
- 2: drift detected (missing tables)

Note:
- This does not compare column-by-column yet; it ensures the migration history
  can bootstrap a fresh DB and that all model tables exist.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_DIR = REPO_ROOT / "instance"
DB_PATH = INSTANCE_DIR / "migration_verify.sqlite"


def _run(cmd: list[str], env: dict[str, str]) -> int:
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    return proc.returncode


def _db_tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def main() -> int:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    env = os.environ.copy()
    env.update(
        {
            "FLASK_ENV": "testing",
            "FLASK_APP": "run:app",
            # Force TestingConfig to use a file-backed SQLite DB
            "TEST_DATABASE_URL": f"sqlite:////{DB_PATH}",
        }
    )

    print(f"[verify] sqlite db: {DB_PATH}")
    rc = _run([str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "flask", "db", "upgrade"], env)
    if rc != 0:
        print("[verify] FAIL: flask db upgrade failed")
        return 1

    # load models metadata
    sys.path.insert(0, str(REPO_ROOT))
    os.environ.setdefault("FLASK_ENV", "testing")
    from run import app  # noqa: F401
    from app.extensions import db

    model_tables = set(db.metadata.tables.keys())
    real_tables = _db_tables(DB_PATH)

    # Ignore Alembic's version table
    real_tables.discard("alembic_version")

    missing = sorted(model_tables - real_tables)
    if missing:
        print("[verify] FAIL: drift detected; missing tables in migrated DB:")
        for t in missing:
            print(f"  - {t}")
        return 2

    print(f"[verify] OK: migrated DB contains all model tables ({len(model_tables)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
