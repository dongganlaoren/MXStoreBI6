# app/forms/sales_forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import (
    DateField,
    DecimalField,
    FileField,
    HiddenField,
    SelectField,
    SubmitField,
)
from wtforms.validators import NumberRange, Optional, DataRequired, InputRequired
from datetime import date

class SalesForm(FlaskForm):
    store_id = SelectField("门店", coerce=str, validators=[InputRequired()])
    report_date = DateField("上报日期", validators=[DataRequired()], format='%Y-%m-%d', default=date.today)
    # POS机营业信息
    cash_income = DecimalField("现金收入 (C)", validators=[DataRequired(), NumberRange(min=0, message="金额不能为负")])
    pos_income = DecimalField("电子支付收入 (P)", validators=[DataRequired(), NumberRange(min=0, message="金额不能为负")])
    voucher_amount = DecimalField("代金券使用金额 (R)", validators=[InputRequired(), NumberRange(min=0, message="金额不能为负")])
    sales_slip_image = FileField("POS机营业信息凭证", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])
    # 第三方外卖平台
    takeaway_amount = DecimalField("第三方外卖平台收入 (T1)", validators=[Optional(), NumberRange(min=0, message="金额不能为负")])
    takeaway_platform_receipt = FileField("第三方外卖平台收入凭证", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])
    # 实际入账
    electronic_actual_arrival = DecimalField("电子支付实际入账金额 (EA)", validators=[DataRequired(), NumberRange(min=0, message="金额不能为负")])
    electronic_actual_arrival_receipt = FileField("电子支付入账凭证", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])
    bank_deposit = DecimalField("银行存款金额 (BC)", validators=[DataRequired(), NumberRange(min=0, message="金额不能为负")])
    bank_fee = DecimalField("银行存款手续费 (BF)", validators=[DataRequired(), NumberRange(min=0, message="金额不能为负")])
    bank_receipt_image = FileField("银行存款凭证", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])
    # 隐藏字段
    initial_load = HiddenField()