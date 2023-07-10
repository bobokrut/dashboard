from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5
from typing import Any, NamedTuple
from urllib.parse import urljoin

from requests import get as r_get
import orjson
import pandas
from dash import dcc, html

from . import ssdl_types as t
import logging
from .parser import parse
from .exceptions import ConfigError
from .visualizations import (
    make_plot,
    make_map,
    make_plot_with_callback,
    Visualization,
)

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


def create_app(app_config: dict[str, Any] | None = None) -> App:
    requests = {}

    logger.info("Initializing app...")

    if app_config is None:
        with open("config.json") as f:
            content = f.read()
        app_config: dict[str, Any] = orjson.loads(content)

    service = t.Service(
        name=app_config["service"]["name"],
        version=t.Version(
            app_config["service"]["version"]["major"],
            app_config["service"]["version"]["minor"],
            app_config["service"]["version"]["patch"],
        ),
        scope=t.Scope(app_config["service"]["scope"].lower()),
    )

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
                plots.append(
                    GridItem(
                        plot=make_map(plot, requests),
                    )
                )
            else:
                if group_by := plot.get("group_by"):
                    comp_id = f"sag-selector-{i}"
                    graph_id = f"sag-plot{i}"
                    func_name = f"update_graph_{i}"
                    plots.append(
                        GridItem(
                            selector=(
                                html.Label(group_by.casefold().capitalize()),
                                dcc.Dropdown(
                                    _get_data(requests, plot["source"], group_by)
                                    .unique()
                                    .sort()
                                    .to_list(),
                                    id=comp_id,
                                ),
                            ),
                            plot_id=graph_id,
                        )
                    )

                    make_plot_with_callback(
                        plot,
                        requests=requests,
                        comp_id=comp_id,
                        graph_id=graph_id,
                        func_name=func_name,
                    )
                else:
                    plots.append(
                        GridItem(
                            plot=make_plot(plot, requests),
                        )
                    )
        except KeyError as e:
            raise ConfigError(f"Missing key {e} in plot {plot['name']}")

        except IndexError as e:
            raise ConfigError(
                f"Invalid config file. Chech if '{plot['name']}.data' has at least 2 items. {plot['data']=}",
                "Please check your config file.",
            )

    return plots


def _get_data(requests, source: str, value: str) -> pandas.Series:
    return requests[source].df[value]
