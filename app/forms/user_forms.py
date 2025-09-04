# app/forms/user_forms.py

from flask_wtf import FlaskForm
# 导入所有需要的字段类型和验证器
from wtforms import (
    BooleanField,
    DateField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    ValidationError,
    FileField,  # 新增
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

# 正确导入模型
from app.models import RoleType, Store, User
from flask import g, session
from app.utils.lang_dict import lang_dict


class LoginForm(FlaskForm):
    """
    用户登录表单 (此表单保持不变)
    """
    username = StringField("用户名", validators=[DataRequired()])
    password = PasswordField("密码", validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField("登录")


class RegistrationForm(FlaskForm):
    # 员工编号，仅分店长/员工注册时必填
    employee_number = StringField("员工编号", validators=[Optional()])
    """
    用户注册表单 (已更新，包含店铺选择)
    """
    username = StringField("用户名", validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField("密码", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "确认密码",
        validators=[DataRequired(), EqualTo("password", message="两次输入的密码必须一致！")]
    )
    role = SelectField(
        "角色",
    # 从 RoleType 枚举动态生成选项（显示使用本地化标签）
    choices=[(role.value, role.name.replace('_', ' ').title()) for role in RoleType],
        validators=[DataRequired("请选择一个角色")]
    )
    # 新增：所属店铺字段。设为 Optional，因为管理组用户不需要选择店铺。
    # 具体的验证逻辑（如“店员必须选店”）将在视图函数中处理。
    store_id = SelectField("所属店铺", choices=[], validators=[Optional()], coerce=str)
    # 新增：管理员创建用户时使用的可选字段
    real_name = StringField("真实姓名", validators=[Optional(), Length(max=100)])
    email = StringField("电子邮箱", validators=[Optional(), Email("请输入有效的邮箱地址"), Length(max=100)])
    phone = StringField("联系电话", validators=[Optional(), Length(max=50)])

    submit = SubmitField("注册")

    def __init__(self, *args, **kwargs):
        """
        在表单初始化时，动态填充“所属店铺”的下拉选项。
        """
        super(RegistrationForm, self).__init__(*args, **kwargs)
    # 从数据库中查询所有店铺，并将其设置为下拉菜单的选项
    self.store_id.choices = [("", "--- (仅门店组人员需要选择) ---")] + \
                [(store.store_id, f"{store.store_id} - {store.store_name}")
                 for store in Store.query.order_by(Store.store_name).all()]
    # 本地化 role choices
    lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
    d = lang_dict.get(lang, lang_dict.get('zh', {}))
    self.role.choices = [(role.value, d.get(f'role_{role.value.lower()}', role.name.replace('_', ' ').title())) for role in RoleType]

    def validate_username(self, field):
        """自定义验证器，确保用户名在注册时不重复"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被使用，请换一个。')

    def validate_employee_number(self, field):
        # 仅分店长/员工角色需要员工编号
        if self.role.data in ['BRANCH_MANAGER', 'EMPLOYEE']:
            if not field.data:
                raise ValidationError('分店长和员工必须填写员工编号。')

            store_id = str(self.store_id.data or '')
            if not store_id:
                # 如果没有选择店铺，这个错误会由 validate_store_id 处理
                return

            val = str(field.data)
            # 校验格式：店铺编号+三位序号
            if not (val.startswith(store_id) and len(val) == len(store_id) + 3 and val[len(store_id):].isdigit()):
                raise ValidationError('员工编号格式应为"店铺编号+三位序号"，如91001。')

            # 唯一性校验：优先尝试整串数字，其次尝试后缀三位数字
            existing_user = None
            emp_num = None
            try:
                if val.isdigit():
                    emp_num = int(val)
            except Exception:
                emp_num = None
            if emp_num is None:
                try:
                    emp_num = int(val[len(store_id):]) if val.startswith(store_id) else None
                except Exception:
                    emp_num = None
            if emp_num is not None:
                existing_user = User.query.filter_by(employee_number=emp_num).first()
            if existing_user:
                raise ValidationError('该员工编号已被使用，请换一个序号。')

    def validate_store_id(self, field):
        # 仅分店长/员工角色必须选择店铺
        if self.role.data in ['BRANCH_MANAGER', 'EMPLOYEE']:
            if not field.data or field.data == '':
                raise ValidationError('作为门店组成员，您必须选择一个所属店铺。')

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False
        # 动态业务校验
        role = self.role.data
        # 需要选择店铺和员工编号的角色
        must_choose_store = ["BRANCH_MANAGER", "EMPLOYEE"]
        if role in must_choose_store:
            if not self.store_id.data or self.store_id.data == '':
                self.store_id.errors.append("该角色必须选择所属店铺")
                return False
            # 修正：employee_number 可能为 int 类型，filters 将空值映射为 0
            emp_num = self.employee_number.data
            if (
                    emp_num is None or
                    (isinstance(emp_num, str) and emp_num.strip() == '') or
                    (isinstance(emp_num, int) and emp_num == 0)
            ):
                self.employee_number.errors.append("该角色必须填写员工编号")
                return False
        return True


class EditProfileForm(FlaskForm):
    """
    【全新】供所有用户编辑自己个人档案的表单。
    这些字段直接对应 User 模型中新增的字段。
    """
    real_name = StringField("真实姓名", validators=[DataRequired("请输入真实姓名"), Length(max=100)])
    employee_number = StringField("员工编号", validators=[Optional()])
    id_card_number = StringField("身份证号", validators=[Optional(), Length(max=100)])

    # 银行信息
    bank_name = StringField("银行名称", validators=[Optional(), Length(max=100)])
    bank_account_number = StringField("银行账号", validators=[Optional(), Length(max=100)])

    # 联系方式
    phone = StringField("联系电话", validators=[Optional(), Length(max=50)])
    line_id = StringField("LINE ID", validators=[Optional(), Length(max=100)])
    email = StringField("电子邮箱", validators=[Optional(), Email("请输入有效的邮箱地址"), Length(max=100)])

    # 在职信息
    start_date = DateField("入职日期", validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField("离职日期", validators=[Optional()], format='%Y-%m-%d')

    # 店铺主要联系人
    is_primary_contact = BooleanField("我是店铺的主要联系人", default=False)

    # 新增：所属门店字段，和注册表单一致
    store_id = SelectField("所属门店", coerce=str, validators=[Optional()])
    # 新增：角色字段，和注册表单一致
    role = SelectField(
        "角色",
        choices=[(role.value, role.name.replace('_', ' ').title()) for role in RoleType],
        validators=[DataRequired("请选择一个角色")]
    )

    # 新增：身份证复印件字段
    id_card_copy = FileField("身份证复印件（图片或PDF，可选）")

    submit = SubmitField("保存我的资料")

    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
    self.store_id.choices = [("", "--- (仅门店组人员需要选择) ---")] + \
                [(str(store.store_id), f"{store.store_id} - {store.store_name}")
                 for store in Store.query.order_by(Store.store_name).all()]
    lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
    d = lang_dict.get(lang, lang_dict.get('zh', {}))
    self.role.choices = [(role.value, d.get(f'role_{role.value.lower()}', role.name.replace('_', ' ').title())) for role in RoleType]

    def validate_employee_number(self, field):
        # 只校验唯一性，不限制格式
        if field.data:
            val = str(field.data)
            try:
                emp_num = int(val)
            except Exception:
                raise ValidationError('员工编号必须为数字。')
            existing_user = User.query.filter_by(employee_number=emp_num).first()
            if existing_user and (not hasattr(self, 'user_id') or existing_user.id != getattr(self, 'user_id', None)):
                raise ValidationError('该员工编号已被使用，请换一个序号。')
