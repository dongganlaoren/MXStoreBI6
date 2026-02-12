# app/forms/cg_bank_statement_forms.py
from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import FileField, PasswordField, SubmitField
from wtforms.validators import Optional


class CgBankStatementUploadForm(FlaskForm):
    pdf_file = FileField('银行流水 PDF')
    submit = SubmitField('上传并解析')


class CgBankStatementPasswordForm(FlaskForm):
    password = PasswordField('PDF 密码', validators=[Optional()])
    submit = SubmitField('重试解析')


class CgBankStatementSaveForm(FlaskForm):
    submit = SubmitField('保存')
