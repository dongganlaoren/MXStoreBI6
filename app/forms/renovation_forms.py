# app/forms/renovation_forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional

from app.models.enums import RenovationTaskPriority, VerificationResult


class RenovationTaskCreateForm(FlaskForm):
    """创建整改任务表单"""
    title = StringField('任务标题', validators=[DataRequired(message='请输入任务标题'), Length(max=255)])
    description = TextAreaField('问题描述', validators=[DataRequired(message='请输入问题描述')])
    # 使用 coerce=str，让表单接受字符串值（例如测试中传入的分类描述，如 'HYGIENE'），在视图中进行解析
    category = SelectField('问题分类', coerce=str,
                           validators=[DataRequired(message='请选择问题分类')])
    priority = SelectField('优先级',
                           choices=[(p.value, p.value) for p in RenovationTaskPriority],
                           default=RenovationTaskPriority.MEDIUM.value,
                           validators=[DataRequired(message='请选择优先级')])
    store_id = SelectField('责任店铺', validators=[DataRequired(message='请选择责任店铺')])
    due_date = DateTimeField('截止时间', format='%Y-%m-%dT%H:%M',
                             validators=[DataRequired(message='请设置截止时间')])
    attachments = MultipleFileField('问题图片/视频',
                                    validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'pdf'],
                                                            '只支持图片、视频和PDF文件')])
    assigned_to = SelectField('责任人', coerce=int, validators=[DataRequired(message='请选择责任人')])
    submit = SubmitField('创建任务')


class RenovationTaskUpdateForm(FlaskForm):
    """更新整改任务表单"""
    task_id = HiddenField()
    evidence_description = TextAreaField('整改说明', validators=[Optional(), Length(max=500)])
    attachments = MultipleFileField('整改证据',
                                    validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'pdf'],
                                                            '只支持图片、视频和PDF文件')])
    submit = SubmitField('上传证据并完成任务')


class RenovationTaskVerifyForm(FlaskForm):
    """验收整改任务表单"""
    task_id = HiddenField()
    verification_result = SelectField('验收结果',
                                      choices=[(r.value, r.value) for r in VerificationResult],
                                      validators=[DataRequired(message='请选择验收结果')])
    verification_comments = TextAreaField('验收意见', validators=[DataRequired(message='请输入验收意见')])
    verification_attachments = MultipleFileField('验收附件',
                                                 validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf'],
                                                                         '只支持图片和PDF文件')])
    submit = SubmitField('提交验收结果')


class RenovationTaskFilterForm(FlaskForm):
    """整改任务筛选表单"""
    status = SelectField('任务状态', choices=[('', '全部状态')], default='')
    priority = SelectField('���先级', choices=[('', '全部优先级')], default='')
    category = SelectField('问题分类', choices=[('', '全部分类')], default='')
    store_id = SelectField('店铺', choices=[('', '全部店铺')], default='')
    date_range = SelectField('时间范围',
                             choices=[
                                 ('', '全部时间'),
                                 ('today', '今天'),
                                 ('week', '本周'),
                                 ('month', '本月'),
                                 ('overdue', '已逾期')
                             ], default='')
    search = StringField('搜索', validators=[Optional(), Length(max=100)])
    submit = SubmitField('筛选')


class RenovationCategoryForm(FlaskForm):
    """整改分类管理表单"""
    name = StringField('分类名称', validators=[DataRequired(message='请输入分类名称'), Length(max=100)])
    parent_id = SelectField('父分类', choices=[('', '无上级分类')], default='')
    description = TextAreaField('分类描述', validators=[Optional(), Length(max=500)])
    sort_order = SelectField('排序权重',
                             choices=[(str(i), str(i)) for i in range(0, 101, 5)],
                             default='0')
    submit = SubmitField('保存分类')
