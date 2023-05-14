import re
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
from boredapp import database, connect_to_api
from boredapp.models import TheUsers, Favourites

api_url = "http://www.boredapi.com/api/activity"


# note: Since we've created an index for the 'email' column, 'username' column and a double column index for the 'activityID' and 'UserID' Column,
# MySQL will automatically use the indexes to optimize our following queries. We don't need to specify the index
# in the query since SQLAlchemy will handle it for us.
# Using the indexes will speed up the search.

def display_the_activity(activityID):
    """
        This function displays an activities' info.
    """

    if activityID is None:
        return "No activity has been selected"

    url = "{}?key={}".format(api_url, activityID)
    activity = connect_to_api(url)

    session[
        "activityID"] = activityID  # saving the activity id into the session for the activity generated - for later use

    activity_name = activity['activity']
    participant_number = activity['participants']
    activity_type = activity['type']
    activity_link = activity['link']

    # this formats the link to the string if a link exists, otherwise and empty string is formatted
    # this also makes the link hyperlinked
    link_str = f"{activity_link}" if activity_link else ""

    return "{}, it's a {} activity and can be done by {} participant{}".format(
        activity_name, activity_type, participant_number, "" if participant_number == 1 else "s"), link_str


def check_if_activity_is_in_favourites(activityID, UserID):
    """
        This function checks the database to see if the activity that the user wants to save is already saved in the database or not.
    """
    favourites_exists = database.session.query(Favourites).filter_by(activityID=activityID, UserID=UserID).first()

    if favourites_exists:  # if True
        return True
    else:  # if False
        return False


# this must be called after a user has logged in, so we can save the user's UserID into the session for later use.
def get_user_id():
    """
        This function checks if an 'email' or 'username' is in the current session and uses this data to search for the users ID number from the database.
    """
    if 'Email' in session:
        # query the user by their email
        current_user = database.session.query(TheUsers).filter_by(Email="{}".format(session['Email'])).first()

    elif 'Username' in session:
        # query the user by their username
        current_user = database.session.query(TheUsers).filter_by(Username="{}".format(session['Username'])).first()

    else:
        return "User is not logged in"

    user_id = current_user.UserID  # select their UserID column

    return user_id


def get_user_firstname():
    """
        This function checks if an 'email' or 'username' is in the current session and uses this data to search for the users Firstname from the database.
    """
    if 'Email' in session:
        # query the user by their email
        current_user = database.session.query(TheUsers).filter_by(Email="{}".format(session['Email'])).first()

    elif 'Username' in session:
        # query the user by their username
        current_user = database.session.query(TheUsers).filter_by(Username="{}".format(session['Username'])).first()

    else:
        return "User is not logged in"

    firstname = current_user.FirstName  # select their FirstName column

    return firstname


def is_user_logged_in():
    """
        This function checks if there is a UserID saved in the current session to verify if a user is currently logged in or not.
    """
    if "UserID" in session:  # if the user has logged in
        return True
    else:
        return False


def reset_user_password(user_email, new_password):
    """
            This function resets the users password in the database to a new password which is hashed.
    """
    current_user = database.session.query(TheUsers).filter_by(Email=user_email).first()
    hashed_password = generate_password_hash(new_password)

    if check_password_hash(current_user.Password,
                           new_password):  # we must use this specific function to check if they are the same (instead of comparing the users current password to the new 'hashed_password') because the hashing algorithm adds a random salt value, so the hash values will be different even for the same password.
        return False

    current_user.Password = hashed_password
    database.session.commit()
    return True


def check_if_strong_password(password):
    """
            This function compares password against regex requirements to determine if it's strong.
    """
    # At least one uppercase letter, one lowercase letter, one digit, and one special character
    regex_requirements = re.compile(
        r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@!#$%^&*_\-])(?!.*[~`\[\]{}()+=\\|;:'\",<.>?/]).{8,}$")

    is_password_strong = regex_requirements.fullmatch(password)  # returns ['0' if True or None is False]

    if is_password_strong:
        return True
    return False
