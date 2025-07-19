from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, FileField, IntegerField, SubmitField, HiddenField, MultipleFileField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from app.models.enums import ReimbursementPrimaryCategory, ReimbursementSecondaryCategory, ReimbursementStatus
from app.models.store import Store
from app.models.user import User

class ReimbursementCreateForm(FlaskForm):
    primary_category = SelectField('一级分类', choices=[(c.name, c.value) for c in ReimbursementPrimaryCategory], validators=[DataRequired()])
    secondary_category = SelectField('二级分类', choices=[], validators=[DataRequired()])
    store_id = SelectField('所属店铺', choices=[], validators=[Optional()])
    reason = TextAreaField('报销事由', validators=[DataRequired(), Length(max=500)])
    submission_date = DateField('日期', validators=[DataRequired()])
    amount = DecimalField('报销金额', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    currency = SelectField('货币单位', choices=[('THB', '泰铢'), ('CNY', '人民币')], default='THB', validators=[DataRequired()])
    approver_id = StringField('审批人', validators=[DataRequired(message='请选择审批人')])
    attachments = MultipleFileField('报销附件', validators=[Optional()])
    submit = SubmitField('提交申请')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import datetime
        if not self.submission_date.data:
            self.submission_date.data = datetime.date.today()
        self.store_id.choices = [(s.store_id, s.store_name) for s in Store.query.order_by(Store.store_name).all()]
        # 动态设置二级分类choices，保证POST校验通过
        primary = self.primary_category.data or (self.primary_category.choices[0][0] if self.primary_category.choices else None)
        secondary_map = {
            'SHARED_COST': [
                ('SHARED_REIMBURSEMENT', '公摊报销'),
                ('AGENCY_ACCOUNTING', '代理记账'),
                ('TAXES', '各种税费'),
                ('EMPLOYEE_SOCIAL_SECURITY', '员工社保'),
                ('OTHER_SHARED_COST', '其它公摊')
            ],
            'STORE_COST': [
                ('MIXTURE_MATERIAL', '蜜雪物料'),
                ('MATERIAL_TRANSPORT', '物料运输'),
                ('FIXED_SALARY', '固定工资'),
                ('TEMPORARY_SALARY', '临时工工资'),
                ('EXTERNAL_LEMON', '外部柠檬'),
                ('STORE_PETTY_CASH', '店铺备用金'),
                ('RENTAL_TAX', '租房税'),
                ('UTILITIES', '水电费'),
                ('STORE_RENT', '店铺房租'),
                ('WAREHOUSE_RENT', '仓库房租'),
                ('OTHER_COST', '其它成本')
            ]
        }
        self.secondary_category.choices = secondary_map.get(primary, [])

class ReimbursementApproveForm(FlaskForm):
    approval_comments = TextAreaField('审批意见', validators=[Optional(), Length(max=500)])
    status = SelectField(
        '审批结果',
        choices=[
            (ReimbursementStatus.APPROVED, '通过'),
            (ReimbursementStatus.REJECTED, '拒绝')
        ],
        validators=[Optional()]  # 允许status为空，审批通过按钮无需提交status
    )
    attachments = FileField('审批附件', validators=[Optional()])
    submit = SubmitField('审批通过')
