# app/forms/attendance_forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, StringField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional, Length
from flask import g, session
from app.utils.lang_dict import lang_dict


class AttendancePunchForm(FlaskForm):
    action = SelectField(
        '打卡类型',
    choices=[('CLOCK_IN', '上班打卡'), ('CLOCK_OUT', '下班打卡')],
        validators=[DataRequired(message='请选择打卡类型')]
    )
    location_name = StringField('位置描述', validators=[Optional(), Length(max=255)])
    latitude = HiddenField('lat')
    longitude = HiddenField('lng')
    photo = FileField('现场照片',
                      validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '仅支持图片文件')])
    notes = TextAreaField('备注', validators=[Optional(), Length(max=500)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lang = getattr(g, 'lang', None) or session.get('lang', 'zh')
        d = lang_dict.get(lang, lang_dict.get('zh', {}))
        self.action.choices = [
            ('CLOCK_IN', d.get('attendance_clock_in', '上班打卡')),
            ('CLOCK_OUT', d.get('attendance_clock_out', '下班打卡'))
        ]
