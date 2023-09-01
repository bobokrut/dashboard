import tracemalloc

import orjson
from asgiref.wsgi import WsgiToAsgi
from dash import dcc, html
from flask import Response, redirect, request
from werkzeug.datastructures import FileStorage
from werkzeug.wrappers import Response as WerkzeugResponse

tracemalloc.start()

import my_dash_component

from .config import App, create_app
from .init_dash import app, server, setup

APP: App = None  # type: ignore


def create_grid():
    grid = []
    for grid_item in APP.plots:
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
    for grid_item in APP.tables:
        grid.append(dcc.Graph(className="w-full", figure=grid_item.plot))

    return grid


def create_layout() -> list[my_dash_component.Container | dcc.Graph]:
    return html.Div(
        [
            dcc.Location(id="sag_url", refresh=False),
            my_dash_component.Navbar(
                id="sag_navbar",
                dashboard_name=APP.service.name,
                dashboard_picture="https://www.fh-krems.ac.at/fileadmin/imc/images/logos/imc-logo-web-preview.png",
                dashboard_version=str(APP.service.version),
            ),
            my_dash_component.Grid(create_grid(), hash=APP.hash, id="sag_grid"),
        ]
    )


def init_dash() -> None:
    global APP
    APP = create_app()
    app.layout = create_layout


@server.route("/")
def index() -> WerkzeugResponse:
    return redirect("/dash/")


@server.route("/config", methods=["POST"])
def change_config() -> Response:
    global APP

    file: FileStorage = list(request.files.values())[0]
    new_config = orjson.loads(file.stream.read().decode("utf-8"))
    file.stream.seek(0)
    file.save("config.json")
    APP = create_app(new_config)
    return Response(status=200)


def create_server() -> WsgiToAsgi:
    setup()
    init_dash()
    # print memory usage
    snapshot = tracemalloc.take_snapshot()
    snapshot.dump("mem_profile.txt")

    return WsgiToAsgi(server)
