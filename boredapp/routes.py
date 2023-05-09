import secrets
from datetime import datetime, timezone, timedelta

import requests
from flask import request, flash, session, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from . import app, connect_to_api, database
from boredapp.boredAppFunctions import is_user_logged_in, get_user_id, get_user_firstname, \
    display_the_activity, check_if_activity_is_in_favourites
import re
from boredapp.models import TheUsers, Favourites
from boredapp.forms import SignUpForm, LogInForm, ForgotPassword
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from .config import client_secrets_file, GOOGLE_CLIENT_ID

APIurl = "http://www.boredapi.com/api/activity"


# create a Flow object using the client secrets file and desired scopes
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)

@app.route("/googlelogin")
def googlelogin():
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
    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    # get the user's ID token and verify it
    credentials = flow.credentials
    jsonWebToken = credentials.id_token
    token_request = google.auth.transport.requests.Request()

    id_info = id_token.verify_oauth2_token(
        id_token=jsonWebToken,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    # validate the token based on the issued_at time
    issued_at = datetime.fromtimestamp(id_info["iat"], timezone.utc)
    valid_delta = timedelta(minutes=15)  # ensures that any access tokens created within the past 15 minutes will be valid, while access tokens issued more than 15 minutes ago will be considered invalid
    if datetime.now(timezone.utc) - issued_at > valid_delta:
        abort(500)  # Token is not yet valid!

    # save the user's profile information to the session
    session["FirstName"] = id_info.get("given_name")
    session["LastName"] = id_info.get("family_name")
    session["Email"] = id_info.get("email")

    # save the user's profile information to the database
    user_exists = database.session.query(TheUsers).filter(TheUsers.Email == session["Email"]).first()

    if user_exists == None : # if the user isn't already in the database
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
@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
        This function allows a user to sign up and checks the database to see if they are already signed up or not + also checks if a user is already logged in.
    """
    if is_user_logged_in() is True:
        return redirect(url_for("user"))
    else:
        firstname = lastname = email = dateofbirth = city = username = password = None
        form = SignUpForm()

        # if a POST request was made from the signup page
        if request.method == "POST":

            # if the inputted form data is all valid.
            if form.validate_on_submit():
                firstname = form.firstname.data
                form.firstname.data = ''
                lastname = form.lastname.data
                form.lastname.data = ''
                email = form.email.data
                form.email.data = ''
                username = form.username.data
                form.username.data = ''
                password = form.password.data
                form.password.data = ''

                password = generate_password_hash(password)

                # Check if there's a user in the database with this username/email already
                # this returns the user row with this email/username or None if it doesn't exist
                user_exists = database.session.query(TheUsers).filter(
                    (TheUsers.Email == email) | (TheUsers.Username == username)).first()

                if user_exists:
                    flash("A User already exists with this email/username.", "error")
                else:
                    # save user into database
                    new_user = TheUsers(FirstName=firstname, LastName=lastname, Email=email,
                                        Username=username, Password=password)  # hash password
                    database.session.add(new_user)
                    database.session.commit()

                    flash("Sign Up Successful!!", "success")
            else:
                flash("Signup details are invalid", "error")

        return render_template("signup.html", firstname=firstname, lastname=lastname, email=email,
                               dateofbirth=dateofbirth,
                               city=city, username=username, password=password, form=form)


@app.route("/login", methods=["POST", "GET"])
def login():
    """
        This function allows a user to log in and check the database to see if their log in credentials are correct + also checks if a user is already logged in.
    """
    if is_user_logged_in() is False:
        emailOrUsername = password = None
        form = LogInForm()

        # if a POST request was made from the signup page
        if request.method == "POST":
            # if the inputted form data is all valid.
            if form.validate_on_submit():
                emailOrUsername = form.emailOrUsername.data
                form.emailOrUsername.data = ''
                password = form.password.data
                form.password.data = ''

                # Check if user used their email or username to login
                # returns a value or none if a user doesn't exist with these matching credentials

                # check if a username or email was entered
                if "@" in emailOrUsername:
                    session['Email'] = emailOrUsername  # saves the users email into the session
                    user = database.session.query(TheUsers).filter_by(Email=emailOrUsername).first()
                else:
                    session['Username'] = emailOrUsername  # saves the users email into the session
                    user = database.session.query(TheUsers).filter_by(Username=emailOrUsername).first()

                # if a user exists in the database with this username/email
                if user:
                    # compare the hashed password from the database to the password the user logged in
                    if check_password_hash(user.Password, password):
                        session['UserID'] = get_user_id()  # save the users ID to a session for later use
                        session['FirstName'] = get_user_firstname()

                        flash("Log in Successful!", "success")
                        return redirect(url_for("user"))

                flash("Log in Unsuccessful, Please try again!", "error")

        return render_template("login.html", emailOrUsername=emailOrUsername, password=password, form=form)

    else:
        return redirect(url_for("user"))

"""
@app.route("/forgotpassword", methods=["POST", "GET"])
def forgotpassword():
"""
        #This function allows a user to reset their password via an external link using their email or username.
"""
    emailOrUsername = None
    form = ForgotPassword()

    # if a POST request was made from the signup page
    if request.method == "POST":
        # if the inputted form data is all valid.
        if form.validate_on_submit():
            emailOrUsername = form.emailOrUsername.data
            form.emailOrUsername.data = ''

            # check if a username or email was entered
            if "@" in emailOrUsername:
                user = database.session.query(TheUsers).filter_by(Email=emailOrUsername).first()
            else:
                user = database.session.query(TheUsers).filter_by(Username=emailOrUsername).first()

            # if a userexists in the database with this username/email
            if user:

                # Generate a unique token
                newToken = secrets.token_urlsafe(16)

                # Update the user's token attribute
                user.token = newToken

                # Commit the changes to the database
                database.session.commit()

                # Send an email with the reset link
                reset_link = url_for('reset_password_confirm', token=newToken, _external=True)
                msg = Message('Password Reset Request', recipients=user.Email)
                msg.body = f"To reset your password, click on the following link: {reset_link}"

                Mail.send(msg)
                flash('An email has been sent with instructions to reset your password.', 'success')

            else:
                flash("No account found with that email or username", "error")

    return render_template("forgotpassword.html", emailOrUsername=emailOrUsername, form=form)


@app.route("/")
def reset_password_confirm():
    pass
"""



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
    if is_user_logged_in() is True:
        all_users_favourites = (
            database.session.query(Favourites.activity, Favourites.participants, Favourites.type,
                                   Favourites.activityID)
            .filter(Favourites.UserID == session["UserID"])
            .all())
        return render_template("favourites.html", users_favourites=all_users_favourites)
    else:
        return redirect(url_for("login"))

@app.route('/favourites/',methods=['GET', 'POST'])
def view_favourites_by_activity_type():
    """
        This function displays a user's favourite activities page if they are logged in or takes them to the login page if they are not.
    """
    if is_user_logged_in() is True:

        activity_type = request.args.get('activity_type')

        if activity_type == "all":
            return redirect(url_for("view_all_favourites"))
        else:

            favourites_by_activity_type = database.session.query(Favourites.activity, Favourites.participants, Favourites.type,
                                   Favourites.activityID).filter_by(UserID=session['UserID'], type=activity_type).all()

            return render_template("favourites.html", users_favourites=favourites_by_activity_type)

    else:
        return redirect(url_for("login"))



@app.route('/favourites/delete/<string:activity_id>', methods=['POST'])
def delete_favourite(activity_id):
    if is_user_logged_in() is True:
        activity_to_delete = database.session.query(Favourites).filter_by(UserID=session['UserID'],
                                                                          activityID=activity_id).first()
        if activity_to_delete:
            database.session.delete(activity_to_delete)
            database.session.commit()
    return redirect(request.referrer) # redirect the user back to the previous page they were on before clicking the "delete" button.


@app.route("/activity")  # < > lets you pass value through to function as a parameter
def activity():
    """
        This function displays a user's activity page if they are logged in or takes them to the login page if they are not.
    """
    if is_user_logged_in() is True:
        return render_template("activityPage.html")
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
    if "Username" or "Email" in session:  # if the user has logged in
        flash("Logged out successfully", "success")

    """session.pop("Username", None)  # removing the data from our session dict
    session.pop("Email", None)  # removing the data from our session dict
    session.pop("password", None)  # removing the data from our session dict
    session.pop("UserID", None)  # removing the data from our session dict
    session.pop("FirstName", None)  # removing the data from our session dict"""
    session.clear()

    return redirect(url_for("home"))  # when we log out ,redirect to the home page


@app.route("/randomActivity", methods=["GET", "POST"])
def randomActivity():
    """
        This function generates a random activity from the api.
    """
    if is_user_logged_in() is True:
        if request.method == 'POST':
            clicked = True
            url = "{}/".format(APIurl)
            activity = connect_to_api(url)

            activityID = activity['key']

            activityInfo, link_str = display_the_activity(activityID)

            return render_template('user.html', activityInfo=activityInfo,
                                   clicked=clicked)
    else:
        return redirect(url_for("login"))


@app.route("/participantNumber", methods=["GET", "POST"])
def participantNumber():
    """
        This function generates an activity from the api based on an inputted number of participants.
    """
    if is_user_logged_in() is True:

        if request.method == 'POST':
            form = request.form  # get the html form
            clicked = True
            number_of_participants = form["participants"]

            # Invalid Input Handling for user input
            regex_requirements = re.compile(r"^[1-5]|8$")

            participant_no_valid = regex_requirements.fullmatch(
                number_of_participants)  # returns ['0' if True or None is False]

            if participant_no_valid:
                url = "{}?participants={}".format(APIurl, number_of_participants)
                activity = connect_to_api(url)

                activityID = activity['key']

                activityInfo, link_str = display_the_activity(activityID)

                return render_template('user.html', activityInfo=activityInfo,
                                       clicked=clicked, number_of_participants=number_of_participants)
            else:
                flash("Enter a Participant number from 1-5 or 8.", "error")
                return render_template("user.html")

    else:
        return redirect(url_for("login"))

@app.route("/freeActivity", methods=["GET", "POST"])
def freeActivity():
    """
        This function generates a free activity from the api.
    """
    if is_user_logged_in() is True:
        if request.method == 'POST':
            clicked = True
            url = "{}?minprice=0&maxprice=0".format(APIurl)
            activity = connect_to_api(url)

            activityID = activity['key']

            activityInfo, link_str = display_the_activity(activityID)

            return render_template('user.html', activityInfo=activityInfo,
                                   clicked=clicked)
    else:
        return redirect(url_for("login"))

@app.route("/activityThatCostsMoney", methods=["GET", "POST"])
def activityThatCostsMoney():
    """
        This function generates an activity from the api that costs money.
    """
    if is_user_logged_in() is True:
        if request.method == 'POST':
            clicked = True

            url = "{}?minprice=0.01&maxprice=1".format(APIurl)
            activity = connect_to_api(url)

            activityID = activity['key']

            activityInfo, link_str = display_the_activity(activityID)

            return render_template('user.html', activityInfo=activityInfo,
                                   clicked=clicked)
    else:
        return redirect(url_for("login"))


@app.route("/activityType", methods=["GET", "POST"])
def activityType():
    """
        This function generates an activity from the api based on an inputted activity type.
    """
    if is_user_logged_in() is True:
        if request.method == 'POST':
            form = request.form  # get the html form
            clicked = True
            activityType = form["activityType"]

            # Invalid Input Handling for user input
            # It is made not case-sensitive
            regex_requirements = re.compile(
                r"\b(education|recreational|social|diy|charity|cooking|relaxation|music|busywork)\b", re.IGNORECASE)

            activity_type_valid = regex_requirements.fullmatch(
                activityType)  # returns ['0' if True or None is False]

            if activity_type_valid:
                url = "{}?type={}".format(APIurl,
                                          activityType.lower())  # .lower(): we make it all lowercase here to ensure we can correctly access the api key without errors since the user input it not case sensitive
                activity = connect_to_api(url)

                activityID = activity['key']

                activityInfo, link_str = display_the_activity(activityID)

                return render_template('user.html', activityInfo=activityInfo,
                                       clicked=clicked, activityType=activityType)
            else:
                flash("Activity Type invalid, try again.", "error")
                return render_template("user.html")

    else:
        return redirect(url_for("login"))


@app.route("/activityLinked", methods=["GET", "POST"])
def activityLinked():
    """
        This function generates an activity from the api that has a link attached to it.
    """
    if is_user_logged_in() is True:
        if request.method == 'POST':

            activity_with_link_found = False

            while not activity_with_link_found:
                url = "{}/".format(APIurl)
                activity = connect_to_api(url)

                if activity['link']:
                    activityID = activity['key']
                    activityInfo, link_str = display_the_activity(activityID)

                    return render_template('user.html', activityInfo=activityInfo, clicked=True, link_str=link_str)

    else:
        return redirect(url_for("login"))


@app.route("/saveActivity", methods=["GET", "POST"])
def saveActivity():
    """
        This function saves an activity into the database and also checks if the activity is already in the database or not.
    """
    if is_user_logged_in() is True:
        activityID = session['activityID']
        UserID = session['UserID']
        activityInfo = display_the_activity(activityID)[0]

        if check_if_activity_is_in_favourites(activityID, UserID) is True:
            flash("Activity already exists in favourites", "error")
        else:
            # Connect to API to get activity info
            url = "{}?key={}".format(APIurl, activityID)
            activity = connect_to_api(url)

            activity_name = activity['activity']
            participant_number = activity['participants']
            activity_type = activity['type']

            # Run query to save activity info
            add_activity = Favourites(activityID=activityID, UserID=UserID, activity=activity_name,
                                      participants=participant_number,
                                      type=activity_type)
            database.session.add(add_activity)
            database.session.commit()

            flash("Activity saved to favourites!", "success")

        return render_template('user.html', clicked=True, activityInfo=activityInfo)
    else:
        return redirect(url_for("login"))

