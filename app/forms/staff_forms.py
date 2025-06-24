# app/forms/staff_forms.py

# 导入 Store 模型，以便我们能查询店铺列表
from app.models import Store
from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, SubmitField

# 【核心修正】: 我们只导入最基础的验证器
from wtforms.validators import DataRequired, Email, Length, Optional


class StaffForm(FlaskForm):
    """
    用于创建或编辑员工详细档案的表单。
    此版本只包含您要求的非空和Email验证。
    """
    store_id = SelectField("所属店铺", validators=[DataRequired("请为员工选择一个所属店铺")], coerce=str)

    # --- 银行信息 ---
    # 根据我们之前的讨论，这些字段设为必填
    bank_account_name = StringField("开户行名称", validators=[DataRequired("请输入开户行名称"), Length(max=64)])
    bank_account_number = StringField("银行卡号", validators=[DataRequired("请输入银行卡号"), Length(max=64)])

    # --- 员工的个人联系方式 ---
    phone = StringField("电话", validators=[Optional(), Length(max=32)])
    line_id = StringField("Line账号", validators=[Optional(), Length(max=64)]) # 不再有自定义验证器
    email = StringField("邮箱地址", validators=[Optional(), Email("请输入一个有效的邮箱地址"), Length(max=100)])

    # --- 在职日期 ---
    start_date = DateField("入职日期", validators=[DataRequired("请选择入职日期")], format='%Y-%m-%d')

    # --- 其他信息 ---
    is_primary_contact = BooleanField("是否为主要联系人", default=False)

    submit = SubmitField("保存员工信息")

    def __init__(self, *args, **kwargs):
        """
        在表单初始化时，动态填充“所属店铺”的下拉选项。
        """
        super(StaffForm, self).__init__(*args, **kwargs)
        # 从数据库中查询所有店铺，并将其设置为下拉菜单的选项
        self.store_id.choices = [("", "---请选择一个店铺---")] + \
                                [(store.store_id, f"{store.store_id} - {store.store_name}")
                                 for store in Store.query.order_by(Store.store_name).all()]