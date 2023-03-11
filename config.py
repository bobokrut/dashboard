from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5
from typing import Literal, Any
from abc import ABC, abstractmethod
from datetime import datetime

import requests
import plotly.express as px
import plotly.graph_objects as go
import polars
import orjson

from env import GEOCODING_KEY


VisualizationType = Literal["LineChart", "Scatter", "BarChart", "Map", "PieChart"]
DataPathType = Literal["Path", "String"]


def get_data_by_group_and_sum(
    _requests: dict[str, Request], path: DataPath, group_by: str
):
    df = _requests[path.source].df
    return df.loc[:, [path.path, group_by]].groupby(group_by)[path.path].sum()


@dataclass(slots=True, init=False)
class App:
    name: str
    version: str
    requests: dict[str, Request]
    plots: list[Visualization]
    hash: Any
    scope: str

    def __init__(self) -> None:
        with open("config.json") as f:
            config = orjson.loads(f.read())

        self.name = config["service"]["name"]
        self.version = ".".join(
            [
                str(config["service"]["version"]["major"]),
                str(config["service"]["version"]["minor"]),
                str(config["service"]["version"]["patch"]),
            ]
        )
        self.scope = config["service"]["scope"]
        self.requests = self.parse_requests_config(
            config["data_sources"]["measurements"]
        )
        self.plots = self.parse_plots_config(config["application"]["visualizations"])
        self.hash = self.calc_hash(str(config["application"]["visualizations"]))

    def parse_requests_config(self, data: dict) -> dict[str, Request]:
        requests = {}
        for name, request in data.items():
            requests[name] = Request(
                url=request["uri"]
                if request["uri"].endswith("entities")
                else request["uri"] + "/v2/entities",
                type=request["type"],
                provider=request["provider"],
                query=Query(request["query"]["type"], request["query"]["select"]),
            )
        return requests

    def parse_plots_config(self, data: dict) -> list[Visualization]:
        plots: list[Visualization] = []
        for plot in data.values():
            if plot["type"] == "Map":
                plots.append(
                    Map(
                        name=plot["name"],
                        type=plot["type"],
                        area=plot.get("extra").get("area")
                        if plot.get("extra")
                        else None,
                        lat=self.get_data(plot["source"], plot["data"][0]).apply(
                            lambda x: x[1]
                        ),
                        lon=self.get_data(plot["source"], plot["data"][0]).apply(
                            lambda x: x[0]
                        ),
                        label=self.get_data(plot["source"], plot["data"][1]),
                        extra={
                            extra: self.get_data(plot["source"], extra).cast(polars.Utf8).fill_null("unknown")
                            for extra in plot["data"][2:]
                        },
                    ).create()
                )
            else:
                plots.append(
                    Plot(
                        name=plot["name"],
                        type=plot["type"],
                        traces=[
                            {
                                "x": self.get_data(trace["x"]),
                                "y": self.get_data(trace["y"]),
                                "name": trace["y"]["value"],
                            }
                            for trace in plot["traces"]
                        ],
                    ).create()
                )
        return plots

    def get_data(self, source, value) -> list:

        return self.requests[source].df[value]

    def calc_hash(self, _hash: str) -> str:
        return md5(_hash.encode()).hexdigest()


@dataclass(slots=True)
class Request:
    url: str
    provider: str
    type: str
    query: Query

    df: polars.DataFrame = field(init=False)

    def __post_init__(self):
        self.request()

    def request(self) -> None:
        resp = requests.get(self.url)
        data = orjson.loads(resp.content)
        data_dict: list[list[Any]] = []

        for entry in data:
            l = []
            for value in self.query.select:
                if entry.get(value):
                    l.append(self.process(entry[value]))
                else:
                    l.append(None)
            data_dict.append(l)

        self.df = polars.DataFrame(data_dict, schema=self.query.select)

    def process(self, entry: dict):
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

    def process_number(self, entry: dict):
        return entry["value"]

    def process_location(self, entry: dict) -> tuple[float, float]:
        return entry["value"]["coordinates"]

    def process_address(self, entry: dict) -> str:
        return entry["value"]["streetAddress"]

    def process_string(self, entry: dict) -> str:
        return entry["value"]

    def process_datetime(self, entry: dict) -> datetime:
        return datetime.strptime(entry["value"], "%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass
class Query:
    type: str
    select: list[str]


@dataclass
class Visualization(ABC):
    name: str
    type: VisualizationType

    @abstractmethod
    def create(self):
        ...


@dataclass(slots=True)
class DataPath:
    source: str
    path: str


@dataclass
class Map(Visualization):
    lat: list
    lon: list
    label: list
    area: str
    extra: dict[str, list]
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
            lat=self.lat,
            lon=self.lon,
            hover_name=self.label,
            hover_data=self.extra,
            mapbox_style="carto-positron",
            title=self.name,
        )

        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>"
            + "<br>".join(
                [
                    "<b>" + key + "</b>: %{customdata[" + str(i) + "]}"
                    for i, key in enumerate(self.extra.keys())
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


@dataclass
class Plot(Visualization):
    traces: list[dict[str, list]]

    def create(self):
        fig = go.Figure()
        if self.type == "LineChart":
            trace = self.traces.pop(0)
            fig.add_scatter(
                x=trace["x"],
                y=trace["y"],
                mode="lines+markers",
                name=trace["name"],
            )
            for trace in self.traces:
                fig.add_scatter(
                    x=trace["x"],
                    y=trace["y"],
                    mode="lines+markers",
                    name=trace["name"],
                )

        elif self.type == "Scatter":
            trace = self.traces.pop(0)

            fig.add_scatter(
                x=trace["x"],
                y=trace["y"],
                mode="markers",
                name=trace["name"],
            )
            for trace in self.traces:
                fig.add_scatter(
                    x=trace["x"], y=trace["y"], mode="markers", name=trace["name"]
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
