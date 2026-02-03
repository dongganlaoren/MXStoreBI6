from __future__ import annotations

from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from wtforms.validators import DataRequired


class StocktakeFilterForm(FlaskForm):
    store_id = SelectField("店铺", validators=[DataRequired()], choices=[])
    check_date = DateField("盘点日期", validators=[DataRequired()], default=date.today)

    submit = SubmitField("查询")
