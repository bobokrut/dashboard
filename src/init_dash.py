import dash
from .user_auth import auth, login_manager
from flask import Flask
from .env import SECRET_KEY


server = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)
server.config["SECRET_KEY"] = SECRET_KEY
server.register_blueprint(auth)
login_manager.init_app(server)
login_manager.login_view = "auth.login_get"


app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname="/dash/",
    external_stylesheets=[
        "/static/tailwind.css",
        "/static/react-resizable-css.css",
        "/static/react-grid-layout-css.css",
    ],
)
