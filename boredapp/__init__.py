import json

import requests
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from boredapp.config import DATABASEPASSWORD, DATABASENAME, SECRET_KEY
from datetime import timedelta

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
app.config['SECRET_KEY'] = f"{SECRET_KEY}"  # secret key for the WTForm forms you create
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:{PASSWORD}@localhost/{DatabaseName}'.format(
    PASSWORD=DATABASEPASSWORD, DatabaseName=DATABASENAME)
# Set the session lifetime to 30 minutes
app.permanent_session_lifetime = timedelta(minutes=30)


# Initialise the database connection
database = SQLAlchemy(app)


def connect_to_api(url):
    response = requests.get(url)
    dataResponse = response.text
    connection = json.loads(
        dataResponse)  # deserializing - turns json string into python dictionary that can be now accessed

    return connection



from boredapp import routes
