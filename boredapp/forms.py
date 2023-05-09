from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, EmailField
from wtforms.validators import DataRequired, EqualTo

# Form for sign up
class SignUpForm(FlaskForm):
    """
        This class creates a submission form for the user sign up
    """
    firstname = StringField("Firstname:", validators=[DataRequired()])
    lastname = StringField("Lastname", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign Up")


# Form for log in
class LogInForm(FlaskForm):
    """
        This class creates a submission form for the user log in
    """
    emailOrUsername = StringField("emailOrUsername:", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


# Form for forgot password
class ForgotPassword(FlaskForm):

    """
        This class creates a submission form for the user forgot password form
    """
    email = EmailField("Email", validators=[DataRequired()])
    submit = SubmitField("Reset Password")


class ResetPassword(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Submit')





"""
app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com' # replace with your email address
app.config['MAIL_PASSWORD'] = 'your-email-password' # replace with your email password

mail = Mail(app)

@app.route('/send_email')
def send_email():
    msg = Message('Test Email', recipients=['recipient@example.com'])
    msg.body = 'This is a test email sent from Flask!'
    mail.send(msg)
    return 'Email sent!'
"""