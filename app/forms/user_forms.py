
# app/forms/user_forms.py

# 正确导入模型
from app.models import RoleType, Store, User
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
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


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
        # 从 RoleType 枚举动态生成选项
        choices=[(role.value, role.name.replace('_', ' ').title()) for role in RoleType],
        validators=[DataRequired("请选择一个角色")]
    )
    # 新增：所属店铺字段。设为 Optional，因为管理组用户不需要选择店铺。
    # 具体的验证逻辑（如“店员必须选店”）将在视图函数中处理。
    store_id = SelectField("所属店铺", coerce=str, validators=[Optional()])

    submit = SubmitField("立即注册")

    def __init__(self, *args, **kwargs):
        """
        在表单初始化时，动态填充“所属店铺”的下拉选项。
        """
        super(RegistrationForm, self).__init__(*args, **kwargs)
        # 从数据库中查询所有店铺，并将其设置为下拉菜单的选项
        self.store_id.choices = [("", "--- (仅门店组人员需要选择) ---")] + \
                                [(store.store_id, f"{store.store_id} - {store.store_name}")
                                 for store in Store.query.order_by(Store.store_name).all()]

    def validate_username(self, field):
        """自定义验证器，确保用户名在注册时不重复"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被使用，请换一个。')

    def validate_employee_number(self, field):
        # 可为空，但如填写则需校验格式和唯一性
        if field.data:
            store_id = self.store_id.data or ''
            val = str(field.data)
            # 校验格式：店铺编号+三位序号
            if not (store_id and val.startswith(store_id) and len(val) == len(store_id) + 3 and val[len(store_id):].isdigit()):
                raise ValidationError('员工编号格式应为“店铺编号+三位序号”，如91123。')
            # 唯一性校验
            existing_user = User.query.filter_by(employee_number=int(val)).first()
            if existing_user:
                raise ValidationError('该员工编号已被使用，请换一个序号。')


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

    submit = SubmitField("保存我的资料")

    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.store_id.choices = [("", "--- (仅门店组人员需要选择) ---")] + \
            [(store.store_id, f"{store.store_id} - {store.store_name}") for store in Store.query.order_by(Store.store_name).all()]
        self.role.choices = [(role.value, role.name.replace('_', ' ').title()) for role in RoleType]

    def validate_employee_number(self, field):
        # 可为空，但如填写则需校验格式和唯一性
        if field.data:
            store_id = self.store_id.data or ''
            val = str(field.data)
            if not (store_id and val.startswith(store_id) and len(val) == len(store_id) + 3 and val[len(store_id):].isdigit()):
                raise ValidationError('员工编号格式应为“店铺编号+三位序号”，如91123。')
            # 唯一性校验（编辑时需排除自己）
            existing_user = User.query.filter_by(employee_number=int(val)).first()
            if existing_user and (not hasattr(self, 'user_id') or existing_user.id != getattr(self, 'user_id', None)):
                raise ValidationError('该员工编号已被使用，请换一个序号。')

