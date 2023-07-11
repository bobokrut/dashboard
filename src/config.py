from __future__ import annotations

import logging
from dataclasses import dataclass, field
from hashlib import md5
from typing import Any, NamedTuple
from urllib.parse import urljoin

import orjson
import pandas
from dash import dcc, html
from requests import get as r_get

from . import ssdl_types as t
from .exceptions import ConfigError
from .parser import parse
from .visualizations import Visualization, make_map, make_plot, make_plot_with_callback

logger = logging.getLogger("dash_app")


@dataclass
class Request:
    url: str
    provider: t.Provider
    type: t.SensorType
    query: Query

    df: pandas.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        if not self.url.endswith("entities"):
            if not self.url.endswith("/"):
                self.url += "/"
            self.url = urljoin(self.url, "v2/entities")

        if "id" not in self.query.select:
            self.query.select.append("id")

        self._request()

    def _request(self) -> None:
        resp = r_get(self.url)
        data = orjson.loads(resp.content)

        if not data:
            raise ValueError("No data received")

        data_list: list[list[Any]] = parse(data, self.query.select)

        self.df = pandas.DataFrame(data_list, columns=self.query.select)


class Query(NamedTuple):
    type: str = ""
    select: list[str] = []


class GridItem(NamedTuple):
    plot: Visualization | None = None
    selector: dcc.Dropdown | None = None
    plot_id: str | None = None


class App(NamedTuple):
    service: t.Service
    requests: dict[str, Request]
    plots: list[GridItem]
    hash: str


def create_app(app_config: dict[str, Any] | None = None) -> App:  # pyright: ignore
    requests = {}

    logger.info("Initializing app...")

    if app_config is None:
        with open("config.json") as f:
            content = f.read()
        app_config: dict[str, Any] = orjson.loads(content)

    service = _create_service(app_config)

    try:
        requests = _parse_requests_config(app_config["data_sources"]["measurements"])
        plots = _parse_plots_config(
            app_config["application"]["visualizations"], requests
        )
        hash = _calc_hash(str(app_config["application"]["visualizations"]))

    except ConfigError as e:
        e.log()
        plots = []
        hash = _calc_hash("empty")

    except Exception as e:
        logger.error(e)
        plots = []
        hash = _calc_hash("empty")

    return App(service, requests, plots, hash)


def _create_service(app_config: dict[str, Any]) -> t.Service:
    return t.Service(
        name=app_config["service"]["name"],
        version=t.Version(
            app_config["service"]["version"]["major"],
            app_config["service"]["version"]["minor"],
            app_config["service"]["version"]["patch"],
        ),
        scope=t.Scope(app_config["service"]["scope"].lower()),
    )


def _calc_hash(_to_hash: str | dict[str, Any]) -> str:
    """
    Calculates the hash of visualizations config part

    :param _to_hash: config str to be hashed
    :return: MD5 hash
    """

    if isinstance(_to_hash, dict):
        _to_hash = str(_to_hash)

    return md5(_to_hash.encode()).hexdigest()


def _parse_requests_config(data: dict[str, Any]) -> dict[str, Request]:
    requests = {}
    for name, request in data.items():
        try:
            requests[name] = Request(
                url=request["uri"],
                type=t.SensorType(request["type"].lower()),
                provider=t.Provider(request["provider"].lower()),
                query=Query(request["query"]["type"], request["query"]["select"]),
            )
        except KeyError as e:
            raise ConfigError(
                f"Invalid config file. Missing key {e} in {name} request.",
                "Please check your config file.",
            )

    return requests


def _parse_plots_config(data: dict[str, Any], requests) -> list[GridItem]:
    plots = []
    for i, plot in enumerate(data.values()):
        try:
            if plot["type"] == "Map":
                plot_item = _parse_plots_config_map(plot, requests)
            else:
                plot_item = _parse_plots_config_plot(plot, requests, i)

            plots.append(plot_item)

        except KeyError as e:
            raise ConfigError(f"Missing key {e} in plot {plot['name']}")

        except IndexError:
            raise ConfigError(
                f"Invalid config file. Chech if '{plot['name']}.data' has at least 2 items. {plot['data']=}",
                "Please check your config file.",
            )

    return plots


def _parse_plots_config_map(plot: dict[str, Any], requests) -> GridItem:
    return GridItem(
        plot=make_map(plot, requests),
    )


def _parse_plots_config_plot(plot: dict[str, Any], requests, i: int) -> GridItem:
    if group_by := plot.get("group_by"):
        comp_id = f"sag-selector-{i}"
        graph_id = f"sag-plot{i}"
        func_name = f"update_graph_{i}"

        make_plot_with_callback(
            plot,
            requests=requests,
            comp_id=comp_id,
            graph_id=graph_id,
            func_name=func_name,
        )
        return GridItem(
            selector=_create_selector(group_by, comp_id, requests, plot["source"]),
            plot_id=graph_id,
        )

    return GridItem(
        plot=make_plot(plot, requests),
    )


def _create_selector(
    group_by: str, comp_id: str, requests: dict[str, Request], source: str
):
    return (
        html.Label(group_by.casefold().capitalize()),
        dcc.Dropdown(
            _get_data(requests, source, group_by).unique().sort().to_list(),
            id=comp_id,
        ),
    )


def _get_data(requests, source: str, value: str) -> pandas.Series:
    return requests[source].df[value]
