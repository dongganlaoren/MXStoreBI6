# app/forms/sales_forms.py
from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional


class SalesForm(FlaskForm):
    """营业额上报表单"""

    store_id = SelectField(
        "店铺", choices=[], validators=[DataRequired(message="请选择店铺")]
    )

    report_date = DateField(
        "营业日期",
        validators=[DataRequired(message="请选择营业日期")],
        format="%Y-%m-%d",
        default=date.today,
    )

    cash_income = FloatField(
        "现金收入",
        validators=[
            Optional(),
            NumberRange(min=0, message="现金收入不能为负数"),
        ],
    )

    pos_income = FloatField(
        "电子支付收入",
        validators=[
            Optional(),
            NumberRange(min=0, message="电子支付收入不能为负数"),
        ],
    )

    voucher_amount = FloatField(
        "代金券使用金额",
        validators=[
            Optional(),
            NumberRange(min=0, message="代金券使用金额不能为负数"),
        ],
    )

    takeaway_amount = FloatField(
        "第三方外卖平台收入",
        validators=[
            Optional(),
            NumberRange(min=0, message="第三方外卖平台收入不能为负数"),
        ],
    )

    electronic_actual_arrival = FloatField(
        "电子支付实际入账金额",
        validators=[
            Optional(),
            NumberRange(min=0, message="电子支付实际入账金额不能为负数"),
        ],
    )

    bank_deposit = FloatField(
        "银行存款金额",
        validators=[
            Optional(),
            NumberRange(min=0, message="银行存款金额不能为负数"),
        ],
    )

    bank_fee = FloatField(
        "银行存款手续费",
        validators=[
            Optional(),
            NumberRange(min=0, message="银行存款手续费不能为负数"),
        ],
    )
