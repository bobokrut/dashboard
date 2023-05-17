import my_dash_component
from .config import App
from init_dash import app, server
from dash import dcc, html
from flask import Flask, redirect, Response, request
from werkzeug.datastructures import FileStorage
import orjson
from asgiref.wsgi import WsgiToAsgi

from typing import Union


def create_layout() -> list[Union[my_dash_component.Container, dcc.Graph]]:
    def create_grid():
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
        return grid

    return html.Div(
        [
            my_dash_component.Navbar(
                id="sag_navbar",
                uni_name=App.name,
                version=str(App.version),
            ),
            my_dash_component.Grid(create_grid(), hash=App.hash, id="sag_grid"),
        ]
    )


def init_dash() -> None:
    App.init()
    app.layout = create_layout


@server.route("/")
def index() -> Response:
    return redirect("/dash/")


@server.route("/config", methods=["POST"])
def change_config() -> None:
    file: FileStorage = list(request.files.values())[0]
    new_config = orjson.loads(file.stream.read().decode("utf-8"))
    file.stream.seek(0)
    file.save("config.json")
    App.init(new_config)
    return Response(status=200)


def create_server() -> Flask:
    global server
    init_dash()
    server = WsgiToAsgi(server)
    return server
