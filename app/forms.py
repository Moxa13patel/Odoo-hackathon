# MultipleFiles/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from wtforms.widgets import ListWidget, CheckboxInput

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class QuestionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=10, max=140)])
    tags = StringField('Tags (comma-separated)', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Post Question')

class AnswerForm(FlaskForm):
    body = TextAreaField('Your Answer', validators=[DataRequired()])
    submit = SubmitField('Submit Answer')

# This is the form you should use for announcements
class BroadcastForm(FlaskForm):
    message = TextAreaField('Broadcast Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send')

class TagMultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()
