import json
from datetime import timedelta

import requests
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from boredapp.config import (
    DATABASENAME,
    DATABASEPASSWORD,
    GOOGLE_CLIENT_ID,
    SECRET_KEY,
    USER,
)

"""
Code Structure reference: 
https://youtu.be/44PvX0Yv368
"""

"""
This code block sets up a Flask web application with a secret key for encryption and a MySQL database for storage. It also initializes a database connection using the SQLAlchemy library, and imports the URL routes and view functions defined in the routes module.
"""

# Initialise the flask app
app = Flask(__name__)

# Set the apps configs
app.config["SECRET_KEY"] = f"{SECRET_KEY}"  # secret key for the WTForm forms you create
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "mysql+pymysql://{USER}:{PASSWORD}@localhost/{DatabaseName}".format(
    USER=USER, PASSWORD=DATABASEPASSWORD, DatabaseName=DATABASENAME
)
# Set the session lifetime to 30 minutes
app.permanent_session_lifetime = timedelta(minutes=30)


# Initialise the database connection
database = SQLAlchemy(app)


GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID


def connect_to_api(url):
    response = requests.get(url)
    dataResponse = response.text
    return json.loads(dataResponse)

from boredapp import routes