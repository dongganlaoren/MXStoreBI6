# app/forms/user_forms.py

# 从我们统一的 app.models 中导入 User 和 RoleType
from app.models import RoleType, User
from flask_wtf import FlaskForm

# 导入我们需要的字段和验证器
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError


class RegistrationForm(FlaskForm):
    """
    用户注册表单
    """
    username = StringField("Username", validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="两次输入的密码必须一致！")]
    )
    # 【核心修正】: 优化角色选择字段的 choices
    # 我们使用一个列表推导式，为每个枚举成员生成一个 (value, label) 元组
    # role.value 是小写的 'employee', 'admin' 等，将作为提交的值
    # role.name.capitalize() 是美化后的大写首字母标签，如 'Employee', 'Admin'，将作为显示给用户的文本
    role = SelectField(
        "Role",
        choices=[(role.value, role.name.capitalize()) for role in RoleType],
        validators=[DataRequired()]
    )
    submit = SubmitField("Register")

    def validate_username(self, field):
        """自定义验证器，确保用户名不重复"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被使用，请换一个。')


class LoginForm(FlaskForm):
    """
    用户登录表单
    """
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField("Login")