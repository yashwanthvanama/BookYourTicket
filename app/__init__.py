from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SECRET_KEY, SQLALCHEMY_DATABASE_URI, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.config.from_object('config')
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

db = SQLAlchemy(app)

# Set up user sessions
from app.models import User

login_manager = LoginManager(app)
login_manager.login_view = 'login'

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{AUTH0_DOMAIN}/.well-known/openid-configuration',
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Set up email
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'bookyourticket.noreply@gmail.com'
app.config['MAIL_PASSWORD'] = 'mprh aodu gwdn flag'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

import base64

# Helper functions/filters
# Define the custom filter function
def base64_encode(value):
    if value is None:
        return ""
    return base64.b64encode(value.encode()).decode()

# Add the filter to Jinja2 environment
app.jinja_env.filters['base64_encode'] = base64_encode

from app import routes
