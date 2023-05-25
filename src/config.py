from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5
from typing import Literal, Any
from urllib.parse import urljoin
from datetime import datetime
from typing import Union

import requests
import plotly.express as px
import plotly.graph_objects as go
import orjson
import pandas
from dash import Input, Output, dcc, html, callback
from dateutil import parser as datetime_parser

from .env import GEOCODING_KEY
from . import ssdl_types as t
import logging

logger = logging.getLogger("dash_app")


class ConfigError(Exception):
    pass


VisualizationType = Literal["LineChart", "Scatter", "BarChart", "Map", "PieChart"]


def calc_hash(_hash: Union[str, list[Any]]) -> str:
    if isinstance(_hash, list):
        _hash = str(_hash)
    return md5(_hash.encode()).hexdigest()


def log_error(error: str, hint: str = "") -> None:
    message = f"\033[91mERROR\033[0m {error}"

    if hint:
        message += "\n" + f"\033[92mHINT\033[0m {hint}"

    logger.error(message)


class App:
    name: str
    version: t.Version
    requests: dict[str, Request]
    plots: list[GridItem]
    hash: Any
    scope: t.Scope

    @staticmethod
    def init(config: Union[dict[str, Any], None] = None) -> None:
        logger.info("Initializing app...")
        if not config:
            with open("config.json") as f:
                content = f.read()
            config = orjson.loads(content)

        App.name = config["service"]["name"]
        App.version = t.Version(
            config["service"]["version"]["major"],
            config["service"]["version"]["minor"],
            config["service"]["version"]["patch"],
        )
        App.scope = t.Scope(config["service"]["scope"])
        try:
            App.requests = App.parse_requests_config(
                config["data_sources"]["measurements"]
            )
            App.plots = []
            App.parse_plots_config(config["application"]["visualizations"])
            App.hash = calc_hash(str(config["application"]["visualizations"]))

        except ConfigError:
            # logged already
            App.plots = []
            App.hash = calc_hash("empty")

        except Exception as e:
            logger.error(e)
            App.plots = []
            App.hash = calc_hash("empty")

    @staticmethod
    def parse_requests_config(data: dict[str, Any]) -> dict[str, Request]:
        requests = {}
        for name, request in data.items():
            try:
                requests[name] = Request(
                    url=request["uri"],
                    type=t.SensorType(request["type"]),
                    provider=t.Provider(request["provider"]),
                    query=Query(request["query"]["type"], request["query"]["select"]),
                )
            except KeyError as e:
                log_error(
                    f"Invalid config file. Missing key {e} in {name} request.",
                    "Please check your config file.",
                )
                raise ConfigError

        return requests

    @staticmethod
    def parse_plots_config(data: dict[str, Any]) -> None:
        for i, plot in enumerate(data.values()):
            try:
                if plot["type"] == "Map":
                    App.plots.append(
                        GridItem(
                            plot=Map(
                                source_name=plot["source"],
                                name=plot["name"],
                                type=plot["type"],
                                area=plot.get("extra").get("area")
                                if plot.get("extra")
                                else None,
                                lat=plot["data"][0],
                                lon=plot["data"][0],
                                label=plot["data"][1],
                                extra=plot["data"][2:],
                            ).create(),
                        )
                    )
                else:
                    if group_by := plot.get("group_by"):
                        comp_id = f"sag-selector-{i}"
                        graph_id = f"sag-plot{i}"
                        func_name = f"update_graph_{i}"
                        App.plots.append(
                            GridItem(
                                selector=(
                                    html.Label(group_by.casefold().capitalize()),
                                    dcc.Dropdown(
                                        App.get_data(plot["source"], group_by)
                                        .unique()
                                        .sort()
                                        .to_list(),
                                        id=comp_id,
                                    ),
                                ),
                                plot_id=graph_id,
                            )
                        )

                        Plot(
                            source_name=plot["source"],
                            name=plot["name"],
                            type=plot["type"],
                            traces=plot["traces"],
                            filter=plot["group_by"],
                        ).add_callback(comp_id, graph_id, func_name)
                    else:
                        App.plots.append(
                            GridItem(
                                plot=Plot(
                                    source_name=plot["source"],
                                    name=plot["name"],
                                    type=plot["type"],
                                    traces=plot["traces"],
                                ).create(),
                            )
                        )
            except KeyError as e:
                log_error(f"Missing key {e} in plot {plot['name']}")
                raise ConfigError

            except IndexError as e:
                log_error(
                    f"Invalid config file. Chech if '{plot['name']}.data' has at least 2 items. {plot['data']=}",
                    "Please check your config file.",
                )
                raise ConfigError

    @staticmethod
    def get_data(source: str, value: str) -> pandas.Series:
        return App.requests[source].df[value]


@dataclass()
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

        self.request()

    def request(self) -> None:
        resp = requests.get(self.url)
        data = orjson.loads(resp.content)

        if not data:
            raise ValueError("No data received")

        data_list: list[list[Any]] = []

        for entry in data:
            l = []

            for value in self.query.select:
                if value_data := entry.get(value):
                    l.append(self.process(value_data, value))
                else:
                    l.append(None)

            data_list.append(l)

        self.df = pandas.DataFrame(data_list, columns=self.query.select)

    def process(self, entry: dict, entry_name: str):
        if not isinstance(entry, dict):
            return entry

        if entry["type"] == "Number":
            return self.process_number(entry)
        elif entry["type"] == "geo:json":
            return self.process_location(entry)
        elif entry["type"] == "PostalAddress":
            return self.process_address(entry)
        elif entry["type"] == "Text":
            return self.process_string(entry)
        elif entry["type"] == "DateTime":
            return self.process_datetime(entry)
        elif entry["type"] == "List":
            return self.process_list(entry)
        elif entry["type"] == "StructuredValue":
            return self.process_structured_value(entry, entry_name)

    def process_number(self, entry: dict[str, float]) -> int | float:
        return entry["value"]

    def process_location(self, entry: dict[str, dict[str, list[float]]]) -> list[float]:
        return entry["value"]["coordinates"]

    def process_address(self, entry: dict[str, dict[str, str]]) -> str:
        return entry["value"]["streetAddress"]

    def process_string(self, entry: dict[str, str]) -> str:
        return entry["value"]

    def process_datetime(self, entry: dict[str, str]) -> datetime:
        return datetime_parser.parse(entry["value"])

    def process_list(self, entry: dict[str, list[Any]]) -> list[Any]:
        return entry["value"]

    def process_structured_value(
        self, entry: dict[str, dict[str, str]], entry_name: str
    ) -> tuple[datetime, datetime]:
        if entry_name == "validity":
            return (
                datetime_parser.parse(entry["value"]["from"]),
                datetime_parser.parse(entry["value"]["to"]),
            )
        raise ValueError(f"StructuredValue type {entry_name} not supported")


@dataclass
class Query:
    type: str
    select: list[str]


@dataclass
class GridItem:
    plot: Union[Visualization, None] = None
    selector: Union[dcc.Dropdown, None] = None
    plot_id: Union[str, None] = None


@dataclass
class Visualization:
    name: str
    type: VisualizationType
    source_name: str

    def create(self) -> None:
        raise NotImplementedError

    def get_data(
        self, path: str, to_series: bool = True
    ) -> Union[pandas.DataFrame, pandas.Series]:
        result: pandas.DataFrame = self.df[path]
        if to_series:
            return result.to_series()
        return result

    def get_data_with_filter(
        self,
        path: str,
        filter_by: str,
        filter: str,
        to_series: bool = True,
        bar_chart: bool = False,
    ) -> Union[pandas.DataFrame, pandas.Series]:
        try:
            if bar_chart:
                filtered_df = self.df[self.df[filter_by] == filter]
                grouped_df = filtered_df.groupby("dateObserved").agg({path: "first"})
                sorted_df = grouped_df.sort_values("dateObserved")
                result = sorted_df[[path]]
            else:
                filtered_df = self.df[self.df[filter_by] == filter]
                result = filtered_df[[path]]
        except KeyError as e:
            sp = str(e).split("\n")
            column_name = sp[0].strip()
            df = sp[3].split(";")[0].strip()
            log_error(
                error=f"{self.type} {self.name}: Column '{column_name}' not found in dataframe {df}",
                hint=f"Check if 'data_sources.measurements.<name>.query.select' has this key",
            )
            raise ConfigError
        if to_series:
            return result.to_series()
        return result

    @property
    def df(self) -> pandas.DataFrame:
        return App.requests[self.source_name].df


# @dataclass(slots=True)
# class DataPath:
#     source: str
#     path: str


@dataclass
class Map(Visualization):
    lat: str
    lon: str
    label: str
    area: str
    extra: list[str]
    center_cache: dict[str, dict[str, float]] = field(default_factory=dict)

    def get_center(self) -> dict[str, float]:
        if self.area in self.center_cache:
            return self.center_cache[self.area]

        result: list[dict[str, dict]] = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": self.area, "format": "json"},
        ).json()

        if not result:
            raise ValueError(f"Could not find location for {self.area}")

        location = {"lat": float(result[0]["lat"]), "lon": float(result[0]["lon"])}
        self.center_cache[self.area] = location
        return location

        # google api deprecated
        result: dict[str, dict] = requests.get(
            f"https://maps.googleapis.com/maps/api/geocode/json?address={self.area}&key={GEOCODING_KEY}"
        ).json()

        if result["status"] != "OK":
            raise ValueError(f"Could not find location for {self.area}")
        location = result["results"][0]["geometry"]["location"]

        self.center_cache[self.area] = location
        location["lon"] = location.pop("lng")
        return location

    def create(self) -> go.Figure:
        fig = px.scatter_mapbox(
            lat=self.get_data(self.lat).apply(lambda x: x[1]),
            lon=self.get_data(self.lon).apply(lambda x: x[0]),
            hover_name=self.get_data(self.label),
            hover_data={
                name: self.df[self.get_data(name)].astype(str).fillna("unknown")
                for name in self.extra
            },
            mapbox_style="carto-positron",
            title=self.name,
        )

        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>"
            + "<br>".join(
                [
                    "<b>" + key + "</b>: %{customdata[" + str(i) + "]}"
                    for i, key in enumerate(self.extra)
                ]
            ),
        )

        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
        )
        if self.area:
            try:
                fig.update_layout(
                    mapbox=dict(
                        center=self.get_center(),
                        zoom=10,
                    )
                )
            except ValueError as e:
                logger.error(e)
        return fig

    def get_data(self, path: str) -> pandas.Series:
        try:
            result = self.df.drop_duplicates(subset="id")[path].reset_index(drop=True)
            return result

        except KeyError as e:
            log_error(
                error=f"Map {self.name}: Column {path} not found in {self.name}",
                hint=f"Check if 'data_sources.measurements.<name>.query.select' has this key",
            )
            raise ConfigError


@dataclass
class Plot(Visualization):
    traces: list[dict[str, str]]
    filter: str = field(default_factory=str)
    graph_id: str = field(init=False)

    def create(self, filter_by: str = None) -> go.Figure:
        fig = go.Figure()
        if self.type == "LineChart":
            for trace in self.traces:
                fig.add_scatter(
                    x=self.get_data(trace["x"])
                    if not self.filter
                    else self.get_data_with_filter(trace["x"], self.filter, filter_by),
                    y=self.get_data(trace["y"])
                    if not self.filter
                    else self.get_data_with_filter(trace["y"], self.filter, filter_by),
                    mode="lines+markers",
                    name=trace["y"],
                )

        elif self.type == "Scatter":
            for trace in self.traces:
                fig.add_scatter(
                    x=self.get_data(trace["x"])
                    if not self.filter
                    else self.get_data_with_filter(trace["x"], self.filter, filter_by),
                    y=self.get_data(trace["y"])
                    if not self.filter
                    else self.get_data_with_filter(trace["y"], self.filter, filter_by),
                    mode="markers",
                    name=trace["y"],
                )
        elif self.type == "BarChart":
            for trace in self.traces:
                fig.add_bar(
                    x=self.get_data("dateObserved").sort()
                    if not self.filter
                    else self.get_data_with_filter(
                        "dateObserved", self.filter, filter_by
                    ).sort(),
                    y=self.get_data(trace)
                    if not self.filter
                    else self.get_data_with_filter(
                        trace, self.filter, filter_by, bar_chart=True
                    ),
                    name=trace,
                )
        elif self.type == "PieChart":
            values = []
            labels = self.traces
            for trace in self.traces:
                values.append(
                    self.get_data(trace).sum()
                    if not self.filter
                    else self.get_data_with_filter(trace, self.filter, filter_by).sum()
                )
            fig.add_pie(values=values, labels=labels, hole=0.3)

        fig.update_layout(
            title=self.name,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            showlegend=True,
            margin=dict(l=20, r=60, t=40, b=20),
        )
        return fig

    def add_callback(self, comp_id: str, graph_id: str, func_name: str) -> None:
        @callback(
            Output(component_id=graph_id, component_property="figure"),
            Input(component_id=comp_id, component_property="value"),
        )
        def _func(input: str) -> go.Figure:
            if input:
                return self.create(input)

            fig = go.Figure()
            fig.update_layout(
                title=self.name,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                showlegend=True,
                margin=dict(l=20, r=60, t=40, b=20),
            )

            return fig

        _func.__name__ = func_name
