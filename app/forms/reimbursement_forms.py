from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, FileField, SubmitField, \
    MultipleFileField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models.enums import ReimbursementPrimaryCategory, ReimbursementStatus
from app.models.store import Store
from flask import g, session
from app.utils.lang_dict import lang_dict


class ReimbursementCreateForm(FlaskForm):
    primary_category = SelectField('一级分类', choices=[(c.name, c.value) for c in ReimbursementPrimaryCategory],
                                   validators=[DataRequired()], default='STORE_COST')  # 默认选中店铺成本
    secondary_category = SelectField('二级分类', choices=[], validators=[DataRequired()])
    store_id = SelectField('所属店铺', choices=[], validators=[Optional()])
    reason = TextAreaField('报销事由', validators=[DataRequired(), Length(max=500)])
    submission_date = DateField('日期', validators=[DataRequired()])
    amount = DecimalField('报销金额', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    currency = SelectField('货币单位', choices=[('THB', '泰铢'), ('CNY', '人民币')], default='THB',
                           validators=[DataRequired()])
    approver_id = StringField('审批人', validators=[DataRequired(message='请选择审批人')])
    # 新增：抄送人字段
    cc_recipients = HiddenField('抄送人', validators=[Optional()])
    attachments = MultipleFileField('报销附件', validators=[Optional()])
    submit = SubmitField('提交申请')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import datetime
        from flask_login import current_user
        if not self.submission_date.data:
            self.submission_date.data = datetime.date.today()
        # 动态设置店铺选项
        user = getattr(current_user, '_get_current_object', lambda: current_user)()
        if user and hasattr(user, 'role'):
            role = user.role.value if hasattr(user.role, 'value') else user.role
            if role in ['ADMIN', 'HEAD_MANAGER', 'FINANCE']:
                # 可选所有店铺，显示“店铺ID 店铺名称”
                self.store_id.choices = [(s.store_id, f"{s.store_id} {s.store_name}") for s in
                                         Store.query.order_by(Store.store_id).all()]
            elif role in ['BRANCH_MANAGER', 'EMPLOYEE']:
                # 只能选自己所属店铺
                if user.store_id:
                    store = Store.query.filter_by(store_id=user.store_id).first()
                    if store:
                        self.store_id.choices = [(store.store_id, f"{store.store_id} {store.store_name}")]
                    else:
                        self.store_id.choices = []
                else:
                    self.store_id.choices = []
            else:
                self.store_id.choices = []
        else:
            self.store_id.choices = []
        # 动态设置二级分类choices，保证POST校验通过
        primary = self.primary_category.data or (
            self.primary_category.choices[0][0] if self.primary_category.choices else None)
        secondary_map = {
            'SHARED_COST': [
                ('SHARED_REIMBURSEMENT', '公摊报销'),
                ('AGENCY_ACCOUNTING', '代理记账'),
                ('TAXES', '各种税费'),
                ('EMPLOYEE_SOCIAL_SECURITY', '员工社保'),
                ('STORE_MANAGEMENT', '店铺管理'),
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
        # 本地化货币显示
        try:
            lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
            d = lang_dict.get(lang, lang_dict.get('zh', {}))
            self.currency.choices = [('THB', d.get('currency_thb', 'THB')), ('CNY', d.get('currency_cny', 'CNY'))]
        except Exception:
            # 在导入阶段或无 app context 时使用默认标签
            self.currency.choices = [('THB', 'THB'), ('CNY', 'CNY')]

    def validate_store_id(self, field):
        # 如果一级分类为公摊成本，store_id必须为空
        if self.primary_category.data == 'SHARED_COST' and field.data:
            raise ValueError('公摊成本无需选择所属店铺')
        # 其他分类必须选择店铺
        if self.primary_category.data == 'STORE_COST' and not field.data:
            raise ValueError('店铺成本必须选择所属店铺')


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
