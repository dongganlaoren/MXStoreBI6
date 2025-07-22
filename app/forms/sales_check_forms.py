# app/forms/sales_check_forms.py
from flask_wtf import FlaskForm
from wtforms import DecimalField, HiddenField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional


class SalesCheckForm(FlaskForm):
    report_id = HiddenField()
    bank_deposit = DecimalField(
        "实际到账金额", validators=[DataRequired(), NumberRange(min=0)]
    )
    # 显性展示误差、实际到账、净收入等字段（只读）
    cash_difference = DecimalField(
        "POS现金收入误差 (A)", render_kw={"readonly": True}
    )
    electronic_difference = DecimalField(
        "POS电子支付误差 (B)", render_kw={"readonly": True}
    )
    electronic_actual_arrival = DecimalField(
        "电子支付实际到账金额", render_kw={"readonly": True}
    )
    actual_sales = DecimalField(
        "单日净收入（自动计算）", render_kw={"readonly": True}
    )
    financial_check_status = SelectField(
        "审核状态",
        choices=[("PENDING", "待审核"), ("APPROVED", "已审核")],
        validators=[DataRequired()],
    )
    remark = TextAreaField("财务备注", validators=[Optional()])
    submit = SubmitField("保存")
