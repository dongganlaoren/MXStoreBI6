# app/views/cg_bank_statement_views.py
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms.cg_bank_statement_forms import CgBankStatementPasswordForm, CgBankStatementUploadForm
from app.models.cg_bank_statement import CgBankStatementFile
from app.services.cg_bank_statement_service import (
    CgPdfPasswordRequired,
    cg_bsave_path,
    cg_md5_file,
)
from app.utils.bank_parser import PARSER_VERSION, BankParserEngine, BankParserPasswordRequired, _json_compatible


def _to_float_or_none(val):
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _to_decimal_or_none(val):
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _normalize_cached_for_validation(cached_summary, cached_txns):
    summary = dict(cached_summary or {})
    for key in ['begin_balance', 'end_balance', 'total_dep_amt', 'total_wdl_amt']:
        summary[key] = _to_decimal_or_none(summary.get(key))
    txns = []
    for t in cached_txns or []:
        txns.append({
            'date': t.get('date'),
            'time': t.get('time'),
            'channel': t.get('channel'),
            'desc': t.get('desc'),
            'deposit': _to_decimal_or_none(t.get('deposit')),
            'withdrawal': _to_decimal_or_none(t.get('withdrawal')),
            'balance': _to_decimal_or_none(t.get('balance')),
        })
    return summary, txns


cg_bank_statement_bp = Blueprint('cg_bank_statement', __name__, url_prefix='/cg/bank-statement')


@cg_bank_statement_bp.route('/', methods=['GET', 'POST'])
@login_required
def upload():
    form = CgBankStatementUploadForm()
    if form.validate_on_submit():
        f = request.files.get('pdf_file')
        if not f or not f.filename:
            flash('请选择 PDF 文件', 'warning')
            return redirect(url_for('cg_bank_statement.upload'))

        filename = secure_filename(f.filename)

        # save temp first to hash
        tmp_dir = os.path.join(current_app.root_path, 'instance', 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, "cg_stmt_{}_{}".format(datetime.now().timestamp(), filename))
        f.save(tmp_path)

        file_hash = cg_md5_file(tmp_path)

        existed = CgBankStatementFile.query.filter_by(file_hash=file_hash).first()
        if existed:
            os.remove(tmp_path)
            flash('文件已导入过，已为你打开解析结果页面。', 'info')
            return redirect(url_for('cg_bank_statement.result', file_id=existed.id))

        abs_path, rel_path = cg_bsave_path(filename, file_hash)
        os.replace(tmp_path, abs_path)

        stmt_file = CgBankStatementFile(
            original_filename=filename,
            storage_path=rel_path,
            file_hash=file_hash,
            bank_code='AUTO',
            is_encrypted=False,
            created_by=getattr(current_user, 'user_id', None),
        )
        db.session.add(stmt_file)
        db.session.commit()

        return redirect(url_for('cg_bank_statement.result', file_id=stmt_file.id))

    return render_template('cg_bank_statement_upload.html', form=form)


@cg_bank_statement_bp.route('/<int:file_id>', methods=['GET', 'POST'])
@login_required
def result(file_id: int):
    stmt_file = CgBankStatementFile.query.get_or_404(file_id)

    pwd_form = CgBankStatementPasswordForm()

    abs_pdf_path = _resolve_abs_path(stmt_file.storage_path)

    summary = None
    validation = None
    need_pwd = False
    txns = []
    txns_page = []
    page = 1
    per_page = 200
    total_count = 0
    total_pages = 1
    start_index = 0

    user_pwd = None
    if pwd_form.validate_on_submit():
        user_pwd = pwd_form.password.data or None

    force_reparse = request.args.get('reparse') in ('1', 'true', 'yes')

    # pagination params
    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1

    try:
        # Re-parse mechanism:
        # - If we have cached results with the same parser version, reuse them (fast).
        # - If parser version changed, force re-parse and overwrite cache.
        should_reparse = force_reparse or (stmt_file.parser_version != PARSER_VERSION) or bool(user_pwd)

        # 如果缓存缺少关键字段（如账期），自动触发重新解析
        if not should_reparse and stmt_file.parsed_summary_json is not None:
            cached_period = (stmt_file.parsed_summary_json or {}).get('period')
            if cached_period in (None, ''):
                should_reparse = True
            if stmt_file.bank_code == 'KBANK':
                cached_txns = stmt_file.parsed_txns_json or []
                if cached_txns and all('details' not in t for t in cached_txns):
                    should_reparse = True
            cached_txns = stmt_file.parsed_txns_json
            if cached_txns in (None, []) and not should_reparse:
                should_reparse = True

        if not should_reparse and stmt_file.parsed_summary_json is not None:
            current_app.logger.info('使用缓存解析结果 file_id=%s hash=%s', stmt_file.id, stmt_file.file_hash)
            cached_summary = stmt_file.parsed_summary_json or {}
            cached_txns = stmt_file.parsed_txns_json or []
            cached_errors = stmt_file.parsed_errors_json or []
            cached_ok = len(cached_errors) == 0

            txns = cached_txns
            summary = {
                'period': cached_summary.get('period'),
                'opening_balance': _to_float_or_none(cached_summary.get('begin_balance')),
                'closing_balance': _to_float_or_none(cached_summary.get('end_balance')),
                'credit_count': cached_summary.get('total_dep_cnt'),
                'credit_total': _to_float_or_none(cached_summary.get('total_dep_amt')),
                'debit_count': cached_summary.get('total_wdl_cnt'),
                'debit_total': _to_float_or_none(cached_summary.get('total_wdl_amt')),
                'currency': 'THB',
            }

            # Recompute validation layers from cached data for accurate display.
            engine = BankParserEngine(abs_pdf_path)
            normalized_summary, normalized_txns = _normalize_cached_for_validation(cached_summary, cached_txns)
            engine.summary = normalized_summary
            engine.transactions = normalized_txns
            _ = engine.validate()
            validation_layers = engine.validation_layers or {}
            validation = {
                'ok': cached_ok,
                'layer1': validation_layers.get('layer1') or {'ok': True, 'message': '汇总笔数/金额校验通过'},
                'layer2': validation_layers.get('layer2') or {'ok': True, 'message': '余额连续性校验通过'},
                'layer3': validation_layers.get('layer3') or {'ok': True, 'message': '总账期初期末校验通过'},
                'errors': cached_errors,
            }
        else:
            current_app.logger.info('执行解析引擎 file_id=%s hash=%s', stmt_file.id, stmt_file.file_hash)
            engine = BankParserEngine(abs_pdf_path, password=user_pwd)
            res = engine.parse_and_validate()
            stmt_file.is_encrypted = False
            if res.bank_type:
                stmt_file.bank_code = res.bank_type

            txns = res.transactions or []

            # cache results by version
            stmt_file.parser_version = PARSER_VERSION
            stmt_file.parsed_summary_json = _json_compatible(res.summary)
            stmt_file.parsed_txns_json = _json_compatible(txns)
            stmt_file.parsed_errors_json = list(res.errors or [])
            stmt_file.parsed_at = datetime.now()

            # summary mapping to template fields
            summary = {
                'period': res.summary.get('period'),
                'opening_balance': _to_float_or_none(res.summary.get('begin_balance')),
                'closing_balance': _to_float_or_none(res.summary.get('end_balance')),
                'credit_count': res.summary.get('total_dep_cnt'),
                'credit_total': _to_float_or_none(res.summary.get('total_dep_amt')),
                'debit_count': res.summary.get('total_wdl_cnt'),
                'debit_total': _to_float_or_none(res.summary.get('total_wdl_amt')),
                'currency': 'THB',
            }

            validation = {
                'ok': res.ok,
                'layer1': res.layer1 or {'ok': True, 'message': '汇总笔数/金额校验通过'},
                'layer2': res.layer2 or {'ok': True, 'message': '余额连续性校验通过'},
                'layer3': res.layer3 or {'ok': True, 'message': '总账期初期末校验通过'},
                'errors': res.errors,
            }

        db.session.commit()

    except (CgPdfPasswordRequired, BankParserPasswordRequired):
        need_pwd = True
        db.session.commit()

    except Exception as e:
        current_app.logger.exception('银行流水解析失败')
        flash('解析失败：{}'.format(e), 'danger')

    # paginate transactions for display
    total_count = len(txns or [])
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    txns_page = (txns or [])[start_index:end_index]

    return render_template(
        'cg_bank_statement_result.html',
        stmt_file=stmt_file,
        summary=summary,
        validation=validation,
        need_password=need_pwd,
        pwd_form=pwd_form,
        txns=txns_page,
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages,
        start_index=start_index,
    )


@cg_bank_statement_bp.route('/<int:file_id>/download', methods=['GET'])
@login_required
def download(file_id: int):
    # download uses send_file; import locally to avoid unused warnings
    from flask import send_file

    stmt_file = CgBankStatementFile.query.get_or_404(file_id)
    abs_pdf_path = _resolve_abs_path(stmt_file.storage_path)
    return send_file(abs_pdf_path, as_attachment=True, download_name=stmt_file.original_filename)


def _resolve_abs_path(storage_path: str) -> str:
    """Resolve storage_path to absolute filesystem path.

    storage_path could be relative to static folder (e.g. uploads/...) or absolute.
    """
    if os.path.isabs(storage_path):
        return storage_path

    # storage_path usually like 'uploads/xxx' -> lives under app/static
    static_root = os.path.join(current_app.root_path, 'static')
    candidate = os.path.join(static_root, storage_path)
    if os.path.exists(candidate):
        return candidate

    # or storage_path already includes 'app/static/uploads..' under project root
    project_root = os.path.abspath(os.path.join(current_app.root_path, os.pardir))
    candidate2 = os.path.join(project_root, storage_path)
    return candidate2
