import flask
from flask_session import Session

app = flask.Flask(__name__)
app.config.from_prefixed_env()
app.config.from_pyfile('./config/settings.cfg')

Session(app)
