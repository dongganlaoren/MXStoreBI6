# app/forms/attendance_forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, StringField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional, Length


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
