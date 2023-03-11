from flask import Flask
import my_dash_component
import dash
from dash import html, dcc
from config import App


def init_dash(server=None, config_file: str | None = None) -> dash.Dash:

    config: App = App()

    if not config_file:
        config_file = "config.json"

    if server:
        app = dash.Dash(__name__, server=server, url_base_pathname="/dash/", external_stylesheets=["/assets/tailwind.css"])

    else:
        app = dash.Dash(__name__, external_stylesheets=["/assets/tailwind.css"])

    app.layout = html.Div(
        [
            my_dash_component.Navbar(
                id="component",
                uni_name=config.name,
                version=config.version,
            ),
            my_dash_component.Grid(
                [
                    dcc.Graph(
                        figure=p, className="w-full h-full"
                    )
                    for p in config.plots
                ],
                hash=config.hash,
            ),
        ]
    )


def create_server(config: str | None = None):
    server = Flask(__name__)
    init_dash(server, config_file=config)
    return server

