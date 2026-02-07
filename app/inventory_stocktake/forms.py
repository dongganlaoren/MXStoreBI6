from __future__ import annotations

from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from wtforms.validators import DataRequired


class StocktakeFilterForm(FlaskForm):
    store_id = SelectField("店铺", validators=[], choices=[])
    check_date = DateField("盘点日期", validators=[DataRequired()], default=date.today)
    start_date = DateField("开始日期", validators=[], default=None)
    end_date = DateField("结束日期", validators=[], default=None)

    submit = SubmitField("查询")
