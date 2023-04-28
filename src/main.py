import my_dash_component
from dash import html, dcc
from .config import App
from init_dash import app, server
from flask import Flask, redirect, Response
from flask_login import (
    login_required,
)


def init_dash(server: Flask = None, config_file: str | None = None) -> None:

    App.init()

    if not config_file:
        config_file = "config.json"

    grid = []
    for grid_item in App.plots:
        if grid_item.selector:
            grid.append(
                my_dash_component.Container(
                    [
                        grid_item.selector[0],
                        grid_item.selector[1],
                        dcc.Graph(className="w-full h-full", id=grid_item.plot_id),
                    ]
                )
            )
        else:
            grid.append(dcc.Graph(className="w-full h-full", figure=grid_item.plot))

    app.layout = html.Div(
        [
            my_dash_component.Navbar(
                id="sag_navbar",
                uni_name=App.name,
                version=str(App.version),
            ),
            my_dash_component.Grid(
                grid,
                hash=App.hash,
            ),
        ]
    )


@server.route("/")
def index() -> Response:
    return redirect("/dash/")


def create_server(config: str | None = None) -> Flask:
    init_dash(server, config_file=config)
    return server
