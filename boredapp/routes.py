from flask import request, flash, session, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from . import app, connect_to_api, database
from boredapp.boredAppFunctions import is_user_logged_in, get_user_id, get_user_firstname, \
    display_the_activity, check_if_activity_is_in_favourites
import re
from boredapp.models import TheUsers, Favourites
from boredapp.forms import SignUpForm, LogInForm, ForgotPassword

APIurl = "http://www.boredapi.com/api/activity"


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
                dateofbirth = form.dateofbirth.data
                form.dateofbirth.data = ''
                city = form.city.data
                form.city.data = ''
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
                    new_user = TheUsers(FirstName=firstname, LastName=lastname, Email=email, DOB=dateofbirth,
                                        City=city,
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


@app.route("/forgotpassword", methods=["POST", "GET"])
def forgotpassword():
    """
        This function allows a user to reset their password via an external link using their email or username.
    """
    emailOrUsername = None
    form = ForgotPassword()

    # if a POST request was made from the signup page
    if request.method == "POST":
        # if the inputted form data is all valid.
        if form.validate_on_submit():
            emailOrUsername = form.emailOrUsername.data
            form.emailOrUsername.data = ''

        # insert something that send a password changer to their email

        flash("Password reset link sent", "success")

    return render_template("forgotpassword.html", emailOrUsername=emailOrUsername, form=form)


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
