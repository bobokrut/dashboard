import my_dash_component
from .config import App
from init_dash import app, server
from dash import dcc, html
from flask import redirect, Response, request
from werkzeug.datastructures import FileStorage
import orjson
from asgiref.wsgi import WsgiToAsgi
import click
import logging
from copy import copy
import sys
from flask_login import login_required

from typing import Union, Optional, Literal


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
def change_config() -> Response:
    file: FileStorage = list(request.files.values())[0]
    new_config = orjson.loads(file.stream.read().decode("utf-8"))
    file.stream.seek(0)
    file.save("config.json")
    App.init(new_config)
    return Response(status=200)


def config_logging() -> None:
    logger = logging.getLogger("dash_app")
    logger.setLevel(logging.DEBUG)

    class ColourizedFormatter(logging.Formatter):
        """
        A custom log formatter class that:

        * Outputs the LOG_LEVEL with an appropriate color.
        * If a log call includes an `extras={"color_message": ...}` it will be used
          for formatting the output, instead of the plain text message.
        """

        level_name_colors = {
            5: lambda level_name: click.style(str(level_name), fg="blue"),
            logging.DEBUG: lambda level_name: click.style(str(level_name), fg="cyan"),
            logging.INFO: lambda level_name: click.style(str(level_name), fg="green"),
            logging.WARNING: lambda level_name: click.style(
                str(level_name), fg="yellow"
            ),
            logging.ERROR: lambda level_name: click.style(str(level_name), fg="red"),
            logging.CRITICAL: lambda level_name: click.style(
                str(level_name), fg="bright_red"
            ),
        }

        def __init__(
            self,
            fmt: Optional[str] = None,
            datefmt: Optional[str] = None,
            style: Literal["%", "{", "$"] = "%",
        ):
            super().__init__(fmt=fmt, datefmt=datefmt, style=style)

        def color_level_name(self, level_name: str, level_no: int) -> str:
            def default(level_name: str) -> str:
                return str(level_name)

            func = self.level_name_colors.get(level_no, default)
            return func(level_name)

        def formatMessage(self, record: logging.LogRecord) -> str:
            recordcopy = copy(record)
            levelname = recordcopy.levelname
            seperator = " " * (8 - len(recordcopy.levelname))
            levelname = self.color_level_name(levelname, recordcopy.levelno)
            if "color_message" in recordcopy.__dict__:
                recordcopy.msg = recordcopy.__dict__["color_message"]
                recordcopy.__dict__["message"] = recordcopy.getMessage()
            recordcopy.__dict__["levelprefix"] = levelname + ":" + seperator
            return super().formatMessage(recordcopy)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(
        ColourizedFormatter(
            "%(levelprefix)s [%(name)s] %(module)s:%(funcName)s:%(lineno)d - %(message)s"
        )
    )
    logger.addHandler(stream_handler)


def secure_dash() -> None:
    global server
    for view_func in server.view_functions:
        if view_func.startswith("/dash/"):
            server.view_functions[view_func] = login_required(
                server.view_functions[view_func]
            )


def create_server() -> WsgiToAsgi:
    global server
    config_logging()
    init_dash()
    secure_dash()
    server = WsgiToAsgi(server)
    return server
