# app/forms/user_forms.py
from app.models.user import RoleType  # 导入 RoleType
from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class RegistrationForm(FlaskForm):
    """
    用户注册表单
    """
    username = StringField("Username", validators=[DataRequired(), Length(min=4, max=20)])  # 用户名，必填，长度 4-20
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])  # 密码，必填，最小长度 6
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])  # 确认密码，必填，必须与密码一致
    # 添加角色选择字段，choices 从 RoleType 枚举生成
    role = SelectField("Role", choices=[(role.value, role.name) for role in RoleType], validators=[DataRequired()])
    submit = SubmitField("Register")  # 提交按钮


class LoginForm(FlaskForm):
    """
    用户登录表单
    """
    username = StringField("Username", validators=[DataRequired()])  # 用户名，必填
    password = PasswordField("Password", validators=[DataRequired()])  # 密码，必填
    submit = SubmitField("Login")  # 提交按钮