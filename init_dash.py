import dash
from flask import Flask
from src.user_auth import user
from flask_login import login_required

server = Flask(__name__)
server.register_blueprint(user)
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

# for view_func in server.view_functions:
#     if view_func.startswith("/dash/"):
#         server.view_functions[view_func] = login_required(server.view_functions[view_func])
