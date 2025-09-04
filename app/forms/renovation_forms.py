# app/forms/renovation_forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional

from app.models.enums import RenovationTaskPriority, VerificationResult
from flask import g, session
from app.utils.lang_dict import lang_dict


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 确定语言（优先使用 g.lang，其次 session，最后回退到 'zh'）
        lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
        zh_dict = lang_dict.get(lang, lang_dict.get('zh', {}))
        # 将枚举值映射到翻译后的标签（譬如 priority_urgent）
        self.priority.choices = [
            (p.value, zh_dict.get(f'priority_{p.value.lower()}', p.value)) for p in RenovationTaskPriority
        ]
        # 本地化字段标签/按钮文本
        try:
            self.title.label.text = zh_dict.get('task_title', self.title.label.text)
            self.description.label.text = zh_dict.get('problem_description', self.description.label.text)
            # category label 没有单独键则回退到中文短语
            self.category.label.text = zh_dict.get('problem_category', zh_dict.get('task_category', self.category.label.text))
            self.priority.label.text = zh_dict.get('task_priority', self.priority.label.text)
            self.store_id.label.text = zh_dict.get('responsible_store', self.store_id.label.text)
            self.due_date.label.text = zh_dict.get('due_date', self.due_date.label.text)
            self.attachments.label.text = zh_dict.get('file_attachments', self.attachments.label.text)
            self.assigned_to.label.text = zh_dict.get('responsible_person', self.assigned_to.label.text)
            self.submit.label.text = zh_dict.get('renovation_create', self.submit.label.text)
        except Exception:
            # 安全回退：不要阻塞表单创建
            pass


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 本地化标签
        try:
            lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
            zh_dict = lang_dict.get(lang, lang_dict.get('zh', {}))
            self.evidence_description.label.text = zh_dict.get('verification_comments', self.evidence_description.label.text)
            self.attachments.label.text = zh_dict.get('improvement_evidence', self.attachments.label.text)
            self.submit.label.text = zh_dict.get('upload_evidence', self.submit.label.text)
        except Exception:
            pass
        lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
        zh_dict = lang_dict.get(lang, lang_dict.get('zh', {}))
        # 使用翻译键 verification_passed / verification_failed
        self.verification_result.choices = [
            (r.value, zh_dict.get(f'verification_{r.value.lower()}', r.value)) for r in VerificationResult
        ]
        # 本地化标签
        try:
            self.verification_result.label.text = zh_dict.get('task_verification', self.verification_result.label.text)
            self.verification_comments.label.text = zh_dict.get('verification_comments', self.verification_comments.label.text)
            self.verification_attachments.label.text = zh_dict.get('reimbursement_attachments', self.verification_attachments.label.text)
            self.submit.label.text = zh_dict.get('renovation_verify_submit', self.submit.label.text)
        except Exception:
            pass


class RenovationTaskFilterForm(FlaskForm):
    """整改任务筛选表单"""
    status = SelectField('任务状态', choices=[('', '全部状态')], default='')
    priority = SelectField('优先级', choices=[('', '全部优先级')], default='')
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
            zh_dict = lang_dict.get(lang, lang_dict.get('zh', {}))
            self.status.label.text = zh_dict.get('task_status', self.status.label.text)
            # 优先级与分类的标签
            self.priority.label.text = zh_dict.get('task_priority', self.priority.label.text)
            self.category.label.text = zh_dict.get('problem_category', self.category.label.text)
            self.store_id.label.text = zh_dict.get('responsible_store', self.store_id.label.text)
            self.date_range.label.text = zh_dict.get('time', self.date_range.label.text)
            self.search.label.text = zh_dict.get('search_tasks', self.search.label.text)
            self.submit.label.text = zh_dict.get('filter', self.submit.label.text)
            # 本地化 date_range choices
            choices_map = {
                '': zh_dict.get('all_time', zh_dict.get('all_stores', '全部时间')),
                'today': zh_dict.get('today', '今天'),
                'week': zh_dict.get('this_week', '本周'),
                'month': zh_dict.get('this_month', '本月'),
                'overdue': zh_dict.get('overdue', '已逾期')
            }
            self.date_range.choices = [(k, v) for k, v in choices_map.items()]
        except Exception:
            pass


class RenovationCategoryForm(FlaskForm):
    """整改分类管理表单"""
    name = StringField('分类名称', validators=[DataRequired(message='请输入分类名称'), Length(max=100)])
    parent_id = SelectField('父分类', choices=[('', '无上级分类')], default='')
    description = TextAreaField('分类描述', validators=[Optional(), Length(max=500)])
    sort_order = SelectField('排序权重',
                             choices=[(str(i), str(i)) for i in range(0, 101, 5)],
                             default='0')
    submit = SubmitField('保存分类')
