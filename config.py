from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5
from typing import Literal, Any
from urllib.parse import urljoin
from dateutil import parser as datetime_parser
from datetime import datetime

import requests
import plotly.express as px
import plotly.graph_objects as go
import polars
import orjson
from dash import Input, Output, dcc, html

from env import GEOCODING_KEY
import ssdl_types as t
from init_dash import app


VisualizationType = Literal["LineChart", "Scatter", "BarChart", "Map", "PieChart"]


def calc_hash(_hash: str | list[Any]) -> str:
    if isinstance(_hash, list):
        _hash = str(_hash)
    return md5(_hash.encode()).hexdigest()


@dataclass(slots=True, init=False)
class App:
    name: str
    version: t.Version
    requests: dict[str, Request]
    plots: list[Visualization]
    selectors: list
    hash: Any
    scope: t.Scope

    def __init__(self) -> None:
        with open("config.json") as f:
            config = orjson.loads(f.read())

        self.name = config["service"]["name"]
        self.version = t.Version(
            config["service"]["version"]["major"],
            config["service"]["version"]["minor"],
            config["service"]["version"]["patch"],
        )
        self.scope = t.Scope(config["service"]["scope"].lower())
        self.requests = self.parse_requests_config(
            config["data_sources"]["measurements"]
        )
        self.plots = []
        self.selectors = []
        self.parse_plots_config(config["application"]["visualizations"])
        self.hash = calc_hash(str(config["application"]["visualizations"]))

    def parse_requests_config(self, data: dict) -> dict[str, Request]:
        requests = {}
        for name, request in data.items():
            requests[name] = Request(
                url=request["uri"],
                type=t.SensorType(request["type"].lower()),
                provider=t.Provider(request["provider"].lower()),
                query=Query(request["query"]["type"], request["query"]["select"]),
            )
        return requests

    def parse_plots_config(self, data: dict):
        for i, plot in enumerate(data.values()):
            if plot["type"] == "Map":
                self.selectors.append(None)
                self.plots.append(
                    Map(
                        df=self.requests[plot["source"]].df,
                        name=plot["name"],
                        type=plot["type"],
                        area=plot.get("extra").get("area")
                        if plot.get("extra")
                        else None,
                        lat=plot["data"][0],
                        lon=plot["data"][0],
                        label=plot["data"][1],
                        extra=plot["data"][2:],
                    ).create()
                )
            else:
                if group_by := plot.get("group_by"):

                    comp_id = f"sag-selector-{i}"
                    graph_id = f"sag-plot{i}"
                    func_name = f"update_graph_{i}"
                    self.plots.append(graph_id)

                    self.selectors.append(
                        (
                            html.Label(group_by.casefold().capitalize()),
                            dcc.Dropdown(
                                self.get_data(plot["source"], group_by)
                                .unique()
                                .to_list(),
                                id=comp_id,
                            ),
                        )
                    )

                    Plot(
                        df=self.requests[plot["source"]].df,
                        name=plot["name"],
                        type=plot["type"],
                        traces=plot["traces"],
                        filter=plot["group_by"],
                    ).add_callback(comp_id, graph_id, func_name)
                else:

                    self.selectors.append(None)

                    self.plots.append(
                        Plot(
                            df=self.requests[plot["source"]].df,
                            name=plot["name"],
                            type=plot["type"],
                            traces=plot["traces"],
                        ).create()
                    )

    def get_data(self, source, value) -> polars.Series:

        return self.requests[source].df[value]


@dataclass(slots=True)
class Request:
    url: str
    provider: t.Provider
    type: t.SensorType
    query: Query

    df: polars.DataFrame = field(init=False)

    def __post_init__(self):
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
        data_list: list[list[Any]] = []

        for entry in data:
            l = []

            for value in self.query.select:

                if value_data := entry.get(value):
                    l.append(self.process(value_data, value))
                else:
                    l.append(None)

            data_list.append(l)

        self.df = polars.DataFrame(data_list, schema=self.query.select)

    def process(self, entry: dict, entry_name: str):

        if not isinstance(entry, dict):
            return entry

        match entry["type"]:
            case "Number":
                return self.process_number(entry)
            case "geo:json":
                return self.process_location(entry)
            case "PostalAddress":
                return self.process_address(entry)
            case "Text":
                return self.process_string(entry)
            case "DateTime":
                return self.process_datetime(entry)
            case "List":
                return self.process_list(entry)
            case "StructuredValue":
                return self.process_structured_value(entry, entry_name)

    def process_number(self, entry: dict):
        return entry["value"]

    def process_location(self, entry: dict) -> tuple[float, float]:
        return entry["value"]["coordinates"]

    def process_address(self, entry: dict) -> str:
        return entry["value"]["streetAddress"]

    def process_string(self, entry: dict) -> str:
        return entry["value"]

    def process_datetime(self, entry: dict) -> datetime:
        return datetime_parser.parse(entry["value"])

    def process_list(self, entry: dict) -> list:
        return entry["value"]

    def process_structured_value(
        self, entry: dict, entry_name: str
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
class Visualization():
    name: str
    type: VisualizationType
    df: polars.DataFrame

    def create(self):
        raise NotImplementedError

    def get_data(self, path: str, to_series: bool = True) -> polars.DataFrame | polars.Series:
        result = self.df.select(polars.col(path))
        if to_series:
            return result.to_series()
        return result

    def get_data_with_filter(self, path: str, filter_by: str, filter: str, to_series: bool = True) -> polars.DataFrame | polars.Series:
        result = self.df.filter(polars.col(filter_by) == filter).select(polars.col(path))
        if to_series:
            return result.to_series()
        return result


@dataclass(slots=True)
class DataPath:
    source: str
    path: str


@dataclass
class Map(Visualization):
    lat: str
    lon: str
    label: list
    area: str
    extra: list[str]
    center_cache: dict[str, dict] = field(default_factory=dict)

    def get_center(self):
        if self.area in self.center_cache:
            return self.center_cache[self.area]

        location: dict = requests.get(
            f"https://maps.googleapis.com/maps/api/geocode/json?address={self.area}&key={GEOCODING_KEY}"
        ).json()["results"][0]["geometry"]["location"]

        self.center_cache[self.area] = location
        location["lon"] = location.pop("lng")
        return location

    def create(self):
        fig = px.scatter_mapbox(
            lat=self.get_data(self.lat).apply(lambda x: x[1]),
            lon=self.get_data(self.lon).apply(lambda x: x[0]),
            hover_name=self.get_data(self.label),
            hover_data={
                name: self.get_data(name)
                .cast(polars.Utf8)
                .fill_null("unknown")
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
            fig.update_layout(
                mapbox=dict(
                    center=self.get_center(),
                    zoom=10,
                )
            )
        return fig

    def get_data(self, path) -> polars.Series:
        return self.df.unique(subset="id").select(polars.col(path)).to_series()


@dataclass
class Plot(Visualization):
    traces: list[dict[str, list]]
    filter: str = field(default_factory=str)
    graph_id: str = field(init=False)

    def create(self, filter_by=None):
        fig = go.Figure()
        traces = self.traces.copy()
        if self.type == "LineChart":
            trace = traces.pop(0)
            fig.add_scatter(
                x=self.get_data(trace["x"]),
                y=self.get_data(trace["y"])
                if not self.filter
                else self
                .get_data_with_filter(trace["y"], self.filter, filter_by),
                mode="lines+markers",
                name=trace["y"],
            )
            for trace in traces:
                fig.add_scatter(
                    x=self.get_data(trace["x"]),
                    y=self.get_data(trace["y"])
                    if not self.filter
                    else self
                    .get_data_with_filter(trace["y"], self.filter, filter_by),
                    mode="lines+markers",
                    name=trace["y"],
                )

        elif self.type == "Scatter":
            trace = traces.pop(0)

            fig.add_scatter(
                x=super().get_data(trace["x"]),
                y=super().get_data(trace["y"])
                if not self.filter
                else super()
                .get_data_with_filter(trace["y"], self.filter, filter_by),
                mode="markers",
                name=trace["y"],
            )
            for trace in traces:
                fig.add_scatter(
                    x=super().get_data(trace["x"]),
                    y=super().get_data(trace["y"])
                    if not self.filter
                    else super()
                    .get_data_with_filter(trace["y"], self.filter, filter_by),
                    mode="markers",
                    name=trace["y"],
                )

        fig.update_layout(
            title=self.name,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            showlegend=True,
            margin=dict(l=20, r=60, t=40, b=20),
        )
        return fig

    def add_callback(self, comp_id, graph_id, func_name):

        @app.callback(
            Output(component_id=graph_id, component_property="figure"),
            Input(component_id=comp_id, component_property="value"),
        )
        def _func(input):

            if input:
                return self.create(input)

            fig = go.Figure()
            fig.update_layout(
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                showlegend=True,
                margin=dict(l=20, r=60, t=40, b=20),
            )

            return fig

        _func.__name__ = func_name
