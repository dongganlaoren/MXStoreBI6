"""One-off schema patch for cg_bank_statement_files parser cache columns.

Use when migrations aren't applied but code expects these columns.
This script is idempotent: it checks INFORMATION_SCHEMA before adding.

Run:
  python scripts/cg_bank_statement_schema_patch.py

It uses DATABASE_URL from environment (.env).
"""

import os

from sqlalchemy import create_engine, text

COLUMNS = {
    'parser_version': "VARCHAR(32) NULL",
    'parsed_summary_json': "JSON NULL",
    'parsed_txns_json': "JSON NULL",
    'parsed_errors_json': "JSON NULL",
    'parsed_at': "DATETIME NULL",
}


def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise SystemExit('DATABASE_URL not set')

    engine = create_engine(url)
    conn = engine.connect()
    trans = conn.begin()
    try:
        for col, ddl in COLUMNS.items():
            exists = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name='cg_bank_statement_files' "
                    "AND column_name=:col"
                ),
                {'col': col},
            ).scalar()

            if exists:
                continue

            conn.execute(text("ALTER TABLE cg_bank_statement_files ADD COLUMN {} {}".format(col, ddl)))
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
