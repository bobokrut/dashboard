import logging
import sys
from copy import copy
from typing import Literal, Optional

import click
import dash
from flask import Flask
from flask_login import login_required

from .env import SECRET_KEY
from .user_auth import auth, login_manager

server = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)


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


def _secure_dash() -> None:
    """Adds login_required to all Dash routes"""

    for view_func in server.view_functions:
        if view_func.startswith("/dash/"):
            server.view_functions[view_func] = login_required(
                server.view_functions[view_func]
            )


def _config_logging() -> None:
    """
    Configs logging for the Dash app by creating a 'dash_app' logger

    Notes
    -----
    Formatter was taken from uvicorn logging config
    """

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


def _setup_server() -> None:
    """Registers blueprints and sets up login_manager"""

    server.config["SECRET_KEY"] = SECRET_KEY
    server.register_blueprint(auth)
    login_manager.init_app(server)
    login_manager.login_view = "auth.login_get"


def setup() -> None:
    """Sets up everything for the Dash app"""

    _config_logging()
    _secure_dash()
    _setup_server()
