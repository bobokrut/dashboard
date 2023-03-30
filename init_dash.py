import dash
from flask import Flask

server = Flask(__name__)
app = dash.Dash(__name__, server=server, url_base_pathname="/dash/", external_stylesheets=["/assets/tailwind.css"])
