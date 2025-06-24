# app/forms/sales_forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed

# 导入我们需要的字段类型和验证器
from wtforms import (
    DateField,
    DecimalField,
    FileField,
    HiddenField,
    SelectField,
    SubmitField,
)
from wtforms.validators import NumberRange, Optional


class SalesForm(FlaskForm):
    """
    营业信息上报表单
    这个文件只包含与 "营业信息上报" 相关的表单。
    """
    # --- 核心字段，用于选择和传递上下文 ---
    store_id = SelectField("选择店铺", validators=[Optional()])
    report_date = DateField("上报日期", validators=[Optional()], format='%Y-%m-%d')
    report_id = HiddenField()

    # --- 第一步: POS机信息字段 ---
    cash_sales = DecimalField("POS现金收入 (C)", validators=[Optional(), NumberRange(min=0)])
    electronic_sales = DecimalField("POS电子支付收入 (P)", validators=[Optional(), NumberRange(min=0)])
    system_takeaway_sales = DecimalField("POS外卖收入 (D)", validators=[Optional(), NumberRange(min=0)])
    voucher_amount = DecimalField("代金券使用金额 (R)", validators=[Optional(), NumberRange(min=0)])
    cash_difference = DecimalField("POS现金收入误差 (A)", validators=[Optional()])
    electronic_difference = DecimalField("POS电子支付误差 (B)", validators=[Optional()])
    sales_slip_image = FileField("POS机小票照片", validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])

    # --- 第二步: 第三方外卖平台收入信息 ---
    takeaway_platform_sales = DecimalField("第三方外卖收入金额 (Q2)", validators=[Optional(), NumberRange(min=0)])
    takeaway_platform_receipt = FileField("第三方外卖平台收入凭证", validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])

    # --- 第三步: 银行存款信息 ---
    bank_deposit = DecimalField("银行存入的现金金额", validators=[Optional(), NumberRange(min=0)])
    bank_fee = DecimalField("存款手续费", validators=[Optional(), NumberRange(min=0)])
    bank_receipt_image = FileField("银行存款凭证", validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'pdf'], '只允许上传图片和PDF文件')])

    # 我们将不再在表单类中定义提交按钮，而是直接在模板中编写 <button> 标签
    # 这样可以更灵活地处理分步提交