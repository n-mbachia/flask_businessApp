from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class VendorInviteForm(FlaskForm):
    """Simple form for admins to invite or promote vendors."""

    email = StringField('Vendor Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    submit = SubmitField('Grant Vendor Access')
