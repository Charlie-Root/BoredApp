import re
import smtplib
import google.auth.transport.requests
from flask import request, flash, session, render_template, redirect, url_for
import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from itsdangerous import TimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from pip._vendor import cachecontrol
from boredapp.boredAppFunctions import is_user_logged_in, get_user_id, get_user_firstname, \
    display_the_activity, check_if_activity_is_in_favourites, reset_user_password, check_if_strong_password
from boredapp.forms import SignUpForm, LogInForm, ForgotPassword, ResetPassword
from boredapp.models import TheUsers, Favourites
from . import app, connect_to_api, database
from .config import client_secrets_file, GOOGLE_CLIENT_ID, MYEMAILPASSWORD, MYEMAIL

APIurl = "http://www.boredapi.com/api/activity"

# create a Flow object using the client secrets file and desired scopes
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email",
            "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


@app.route("/google_login")
def google_login():
    """
    Redirects the user to the Google Login page to authorize the application
    to access their profile information.
    """
    # get the authorization URL and state from the Flow object
    authorization_url, state = flow.authorization_url()
    # save the state in the session for later use
    session["state"] = state
    # redirect the user to the authorization URL
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    """
    Handles the callback request from Google after the user has authorized
    the application to access their profile information.
    """
    # fetch the token from the authorization response
    flow.fetch_token(authorization_response=request.url)

    # check if the state in the session matches the state in the request args
    if session["state"] != request.args["state"]:
        abort(500)  # State does not match!

    # get the user's ID token and verify it
    print(flow)
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=300  # This provides a grace period for slight clock differences between the Google
        # server's clock and the client's clock during token verification. The time difference between the two clocks
        # can be up to 5 minutes for the token to be valid.

    )

    # save the user's profile information to the session
    session["FirstName"] = id_info.get("given_name").capitalize()
    session["LastName"] = id_info.get("family_name").capitalize()
    session["Email"] = id_info.get("email").lower()

    # save the user's profile information to the database
    user_exists = database.session.query(TheUsers).filter(TheUsers.Email == session["Email"]).first()

    if user_exists is None:  # if the user isn't already in the database
        # create a new user object
        new_user = TheUsers(FirstName=session["FirstName"], LastName=session["LastName"], Email=session["Email"])
        # add the user to the database
        database.session.add(new_user)
        database.session.commit()
        # show a success message to the user
        flash("Sign Up Successful!!", "success")

    # save the user's ID to the session for later use
    session['UserID'] = get_user_id()

    # redirect the user to the user page
    return redirect(url_for("user"))


# FLASK APP SERVER FUNCTIONS
@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    """
        This function allows a user to sign up and checks the database to see if they are already signed up or not + also checks if a user is already logged in.
    """
    if is_user_logged_in() is True:
        return redirect(url_for("user"))
    firstname = lastname = email = dateofbirth = city = username = password = None
    form = SignUpForm()

    if request.method == "POST":
        if form.validate_on_submit() and check_if_strong_password(form.password.data) is True:
            firstname = form.firstname.data.capitalize()
            form.firstname.data = ''
            lastname = form.lastname.data.capitalize()
            form.lastname.data = ''
            email = form.email.data.lower()
            form.email.data = ''
            username = form.username.data.lower()
            password = form.password.data
            form.password.data = ''

            form.username.data = ''
            password = generate_password_hash(password)

            if (
                user_exists := database.session.query(TheUsers)
                .filter(
                    (TheUsers.Email == email) | (TheUsers.Username == username)
                )
                .first()
            ):
                flash("A User already exists with this email/username.", "error")
            else:
                # save user into database
                new_user = TheUsers(FirstName=firstname, LastName=lastname, Email=email,
                                    Username=username, Password=password)  # hash password
                database.session.add(new_user)
                database.session.commit()

                flash("Sign Up Successful!!", "success")

        else:
            flash("A stronger password is needed", "error")

    return render_template("signup.html", firstname=firstname, lastname=lastname, email=email,
                           dateofbirth=dateofbirth,
                           city=city, username=username, password=password, form=form)


@app.route("/login", methods=["POST", "GET"])
def login():
    """
        This function allows a user to log in and check the database to see if their log in credentials are correct + also checks if a user is already logged in.
    """
    if is_user_logged_in() is not False:
        return redirect(url_for("user"))
    email_or_username = password = None
    form = LogInForm()

    # if a POST request was made from the sign_up page
    if request.method == "POST" and form.validate_on_submit():
        email_or_username = form.email_or_username.data.lower()
        form.email_or_username.data = ''
        password = form.password.data
        form.password.data = ''
    
        # Check if user used their email or username to login
        # returns a value or none if a user doesn't exist with these matching credentials
    
        # check if a username or email was entered
        if "@" in email_or_username:
            session['Email'] = email_or_username  # saves the users email into the session
            user = database.session.query(TheUsers).filter_by(Email=email_or_username).first()
            googleAccountUser=database.session.query(TheUsers).filter_by(Email=email_or_username, Password=None).first()
    
        else:
            googleAccountUser = None
            session['Username'] = email_or_username  # saves the users email into the session
            user = database.session.query(TheUsers).filter_by(Username=email_or_username).first()
    
        if googleAccountUser:
            flash("A Google account already exists with this email. Please login with Google.", "error")
        elif user and check_password_hash(user.Password, password):                    # compare the hashed password from the database to the password the user logged in
            session['UserID'] = get_user_id()  # save the users ID to a session for later use
            session['FirstName'] = get_user_firstname()
    
            flash("Log in Successful!", "success")
            return redirect(url_for("user"))
        else:
            flash("Log in Unsuccessful, Please try again!", "error")
    
        session.pop('Email', None)
        session.pop('Username', None)


    return render_template("login.html", email_or_username=email_or_username, password=password, form=form)


@app.route("/forgot_password", methods=["POST", "GET"])
def forgot_password():
    """
            This function sends a reset password link to a users email.
    """
    form = ForgotPassword()
    if form.validate_on_submit():
        user_email = form.email.data.lower()

        if (
            user_exists := database.session.query(TheUsers)
            .filter(TheUsers.Email == user_email, TheUsers.Password != None)
            .first()
        ):
            # Generate a unique token for the user
            ts = TimedSerializer(app.secret_key)
            token = ts.dumps(user_email, salt='reset-password')

            # Generate reset password link
            reset_password_url = url_for('reset_password', token=token, _external=True)

            with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                smtp.starttls()
                smtp.login(MYEMAIL, MYEMAILPASSWORD)
                subject = 'Reset Your Password'
                body = f"Click the following link to reset your BoredApp password: {reset_password_url}"
                message = f'Subject: {subject}\n\n{body}'
                smtp.sendmail('from@example.com', user_email,
                              message)  # Email the user with a link to reset their password

        flash("A password reset link will be sent to this email if this user exists.", "success")
    return render_template('forgotpassword.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
            This function resets a users password.
    """
    ts = TimedSerializer(app.secret_key)

    try:
        email = ts.loads(token, salt='reset-password', max_age=900) # token is valid for 15 mins max
    except Exception:
        flash("Expired token. Go back to forgot password to generate a new link.", "error")
        return redirect(url_for('forgot_password'))
    form = ResetPassword()

    if form.validate_on_submit():
        if check_if_strong_password(form.password.data) is True:
            # Process the form submission
            new_password = form.confirm_password.data
            if is_reset_successful := reset_user_password(email, new_password):
                flash("Password updated successfully", "success")
                if is_user_logged_in() is True:
                    return redirect(url_for("logout"))
                return redirect(url_for("login"))
            else:
                flash("New password cannot be the same as the current password", "error")
        elif check_if_strong_password(form.password.data) is False:
            flash("A stronger password is needed", "error")

    return render_template('resetpassword.html', form=form)


@app.route("/")
def home():
    """
        This function displays the homepage.
    """
    return render_template("home.html")


@app.route("/favourites")
def view_all_favourites():
    """
        This function displays a user's favourite activities page if they are logged in or takes them to the login page if they are not.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    all_users_favourites = (
        database.session.query(Favourites.activity, Favourites.participants, Favourites.type,
                               Favourites.link,Favourites.activityID, )
        .filter(Favourites.UserID == session["UserID"])
        .all())
    return render_template("favourites.html", users_favourites=all_users_favourites)


@app.route('/favourites/', methods=['GET', 'POST'])
def view_favourites_by_activity_type():
    """
        This function displays a user's favourite activities page if they are logged in or takes them to the login page if they are not.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    activity_type = request.args.get('activity_type')

    if activity_type == "all":
        return redirect(url_for("view_all_favourites"))
    favourites_by_activity_type = database.session.query(Favourites.activity, Favourites.participants,
                                                         Favourites.type,Favourites.link,
                                                         Favourites.activityID).filter_by(
        UserID=session['UserID'], type=activity_type).all()

    return render_template("favourites.html", users_favourites=favourites_by_activity_type)


@app.route('/favourites/delete/<string:activity_id>', methods=['POST'])
def delete_favourite(activity_id):
    """
            This function deleted an activity from the favourites.
    """
    if is_user_logged_in() is True:
        if (
            activity_to_delete := database.session.query(Favourites)
            .filter_by(UserID=session['UserID'], activityID=activity_id)
            .first()
        ):
            database.session.delete(activity_to_delete)
            database.session.commit()
    return redirect(
        request.referrer)  # redirect the user back to the previous page they were on before clicking the "delete" button.


@app.route("/activity")  # < > lets you pass value through to function as a parameter
def activity():
    """
        This function displays a user's activity page if they are logged in or takes them to the login page if they are not.
    """
    if is_user_logged_in() is True:
        return render_template("activitypage.html")
    else:
        return redirect(url_for("login"))


@app.route("/user", methods=["POST", "GET"])
def user():
    """
        This function displays a user's user page if they are logged in or takes them to the login page if they are not.
    """
    if is_user_logged_in() is True:
        return render_template("user.html")
    else:
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    """
        This function removes the user's data from the current session to log them out and redirects the user to the home page of the app.
    """
    flash("Logged out successfully", "success")

    session.clear()

    return redirect(url_for("home"))  # when we log out ,redirect to the home page


@app.route("/random_activity", methods=["GET", "POST"])
def random_activity():
    """
        This function generates a random activity from the api.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    if request.method == 'POST':
        clicked = True
        url = f"{APIurl}/"
        activity = connect_to_api(url)

        activity_id = activity['key']

        activity_info, link_str = display_the_activity(activity_id)

        return render_template('user.html', activityInfo=activity_info,
                               clicked=clicked)


@app.route("/participant_number", methods=["GET", "POST"])
def participant_number():
    """
        This function generates an activity from the api based on an inputted number of participants.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    if request.method == 'POST':
        form = request.form  # get the html form
        number_of_participants = form["participants"]

        # Invalid Input Handling for user input
        regex_requirements = re.compile(r"^[1-5]|8$")

        if participant_no_valid := regex_requirements.fullmatch(
            number_of_participants
        ):
            url = f"{APIurl}?participants={number_of_participants}"
            activity = connect_to_api(url)

            activity_id = activity['key']

            activity_info, link_str = display_the_activity(activity_id)

            clicked = True
            return render_template('user.html', activityInfo=activity_info,
                                   clicked=clicked, number_of_participants=number_of_participants)
        else:
            flash("Enter a Participant number from 1-5 or 8.", "error")
            return render_template("user.html")


@app.route("/free_activity", methods=["GET", "POST"])
def free_activity():
    """
        This function generates a free activity from the api.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    if request.method == 'POST':
        clicked = True
        url = f"{APIurl}?minprice=0&maxprice=0"
        activity = connect_to_api(url)

        activity_id = activity['key']

        activity_info, link_str = display_the_activity(activity_id)

        return render_template('user.html', activityInfo=activity_info,
                               clicked=clicked)


@app.route("/activity_that_costs_money", methods=["GET", "POST"])
def activity_that_costs_money():
    """
        This function generates an activity from the api that costs money.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    if request.method == 'POST':
        clicked = True

        url = f"{APIurl}?minprice=0.01&maxprice=1"
        activity = connect_to_api(url)

        activity_id = activity['key']

        activity_info, link_str = display_the_activity(activity_id)

        return render_template('user.html', activityInfo=activity_info,
                               clicked=clicked)


@app.route("/activity_type", methods=["GET", "POST"])
def activity_type():
    """
        This function generates an activity from the api based on an inputted activity type.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    if request.method == 'POST':
        form = request.form  # get the html form
        activity_type = form["activity_type"]

        # Invalid Input Handling for user input
        # It is made not case-sensitive
        regex_requirements = re.compile(
            r"\b(education|recreational|social|diy|charity|cooking|relaxation|music|busywork)\b", re.IGNORECASE)

        if activity_type_valid := regex_requirements.fullmatch(activity_type):
            url = f"{APIurl}?type={activity_type.lower()}"
            activity = connect_to_api(url)

            activity_id = activity['key']

            activity_info, link_str = display_the_activity(activity_id)

            clicked = True
            return render_template('user.html', activityInfo=activity_info,
                                   clicked=clicked, activityType=activity_type)
        else:
            flash("Activity Type invalid, try again.", "error")
            return render_template("user.html")


@app.route("/activity_linked", methods=["GET", "POST"])
def activity_linked():
    """
        This function generates an activity from the api that has a link attached to it.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    if request.method == 'POST':

        while True:
            url = f"{APIurl}/"
            activity = connect_to_api(url)

            if activity['link']:
                activity_id = activity['key']
                activity_info, link_str = display_the_activity(activity_id)

                return render_template('user.html', activityInfo=activity_info, clicked=True, link_str=link_str)


@app.route("/save_activity", methods=["GET", "POST"])
def save_activity():
    """
        This function saves an activity into the database and also checks if the activity is already in the database or not.

        Right now this function can only save one activity for one user, as the activityID is the primary key.
    """
    if is_user_logged_in() is not True:
        return redirect(url_for("login"))
    activity_id = session['activityID']
    user_id = session['UserID']
    activity_info, link_str = display_the_activity(activity_id)

    if check_if_activity_is_in_favourites(activity_id, user_id) is True:
        flash("Activity already exists in favourites", "error")
    else:
            # Connect to API to get activity info
        url = f"{APIurl}?key={activity_id}"
        activity = connect_to_api(url)

        activity_name = activity['activity']
        participant_number = activity['participants']
        activity_type = activity['type']

        # Run query to save activity info
        add_activity = Favourites(activityID=activity_id, UserID=user_id, activity=activity_name,
                                  participants=participant_number,
                                  type=activity_type, link=link_str)
        database.session.add(add_activity)
        database.session.commit()

        flash("Activity saved to favourites!", "success")

    return render_template('user.html', activityInfo=activity_info, clicked=True, link_str=link_str)
