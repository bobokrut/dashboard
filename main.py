import my_dash_component
from dash import html, dcc
from config import App
from init_dash import app, server


def init_dash(server=None, config_file: str | None = None):

    config: App = App()

    if not config_file:
        config_file = "config.json"

    grid = []
    for p, s in zip(config.plots, config.selectors):
        if s:
            grid.append(
                my_dash_component.Container(
                    [
                        s[0],
                        s[1],
                        dcc.Graph(className="w-full h-full", id=p)
                    ]
                )
            )
        else:
            grid.append(dcc.Graph(className="w-full h-full", figure=p))


    app.layout = html.Div(
        [
            my_dash_component.Navbar(
                id="sag_navbar",
                uni_name=config.name,
                version=str(config.version),
            ),
            my_dash_component.Grid(
                grid,
                hash=config.hash,
            ),
        ]
    )


def create_server(config: str | None = None):
    init_dash(server, config_file=config)
    return server
