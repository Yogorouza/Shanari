import flask

app = flask.Flask(__name__)
app.config.from_prefixed_env()
app.config.from_pyfile('./config/settings.cfg')
