from flask_wtf import FlaskForm
from wtforms import FileField, FloatField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange


class ReimbursementForm(FlaskForm):
    """报销申请表单（员工/分店长填写，包含必要字段验证和文件上传）"""

    primary_category = SelectField(
        "主分类", choices=[], validators=[DataRequired(message="请选择主分类")]
    )

    amount = FloatField(
        "报销金额",
        validators=[
            DataRequired(message="请输入报销金额"),
            NumberRange(min=0.01, message="报销金额必须大于0"),
        ],
    )

    description = TextAreaField(
        "费用说明", validators=[DataRequired(message="请输入费用说明")]
    )

    invoice_file = FileField(
        "发票或收据照片",
        validators=[DataRequired(message="请上传发票或收据照片")],
    )

    submit = SubmitField("提交申请")


class ReimbursementReviewForm(FlaskForm):
    """报销审核表单（区域经理/财务审核使用）"""

    status = SelectField(
        "审核状态",
        choices=[],
        validators=[DataRequired(message="请选择审核状态")],
    )

    review_notes = TextAreaField(
        "审核意见", description="请填写审核意见（拒绝时必填）"
    )

    submit = SubmitField("提交审核")
