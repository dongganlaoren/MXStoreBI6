# app/models/cg_bank_statement.py
from __future__ import annotations

from datetime import datetime

from app.extensions import db


class CgBankStatementFile(db.Model):
    """成本治理：银行流水导入文件（按文件哈希去重）。"""

    __tablename__ = 'cg_bank_statement_files'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    original_filename = db.Column(db.String(255), nullable=False, comment='原始文件名')
    storage_path = db.Column(db.String(512), nullable=False, comment='存储相对路径（相对 static 或 upload 根）')

    file_hash = db.Column(db.String(64), nullable=False, unique=True, index=True, comment='文件哈希（如MD5）')

    bank_code = db.Column(db.String(32), nullable=False, comment='银行类型：BBL/KBank')

    is_encrypted = db.Column(db.Boolean, default=False, comment='是否加密PDF')

    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True, comment='上传人')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    # Parser and cached results (so we can re-parse when parser changes)
    parser_version = db.Column(db.String(32), nullable=True)
    parsed_summary_json = db.Column(db.JSON, nullable=True)
    parsed_txns_json = db.Column(db.JSON, nullable=True)
    parsed_errors_json = db.Column(db.JSON, nullable=True)
    parsed_at = db.Column(db.DateTime, nullable=True)


class CgBankStatementTxn(db.Model):
    """成本治理：银行流水交易明细（按复合键去重）。"""

    __tablename__ = 'cg_bank_statement_txns'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_id = db.Column(db.Integer, db.ForeignKey('cg_bank_statement_files.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    txn_date = db.Column(db.String(16), nullable=False, index=True, comment='日期 YYYY-MM-DD')
    txn_time = db.Column(db.String(16), nullable=True, comment='时间 HH:MM(:SS)')

    description = db.Column(db.String(255), nullable=True, comment='描述')

    credit = db.Column(db.Float, nullable=False, default=0.0, comment='进账金额')
    debit = db.Column(db.Float, nullable=False, default=0.0, comment='出账金额')
    balance = db.Column(db.Float, nullable=False, default=0.0, comment='余额')

    raw_row_hash = db.Column(db.String(64), nullable=False, index=True, comment='用于追溯的行hash')

    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        db.UniqueConstraint('txn_date', 'txn_time', 'credit', 'debit', 'balance', name='uq_cg_stmt_d_t_amt_bal'),
    )
