from __future__ import annotations

from pydantic import BaseModel
from enum import StrEnum, auto
from dataclasses import dataclass, Field
from typing import (
    ClassVar,
    TypeAlias,
    Protocol,
    TypeVar,
    Any,
    Iterable,
    Generic,
    Self,
    runtime_checkable,
)
from urllib.parse import ParseResult as URI
from iso6709.iso6709 import Location  # type: ignore
from datetime import datetime

"""
Globals section / Wraps / Protocols
"""


@runtime_checkable
class Parse(Protocol):
    """
    A type that can be parsed from a stream.
    """

    @classmethod
    def parse(cls, input: str, /) -> tuple[Self, str]:
        """
        Takes a stream of text and returns a tuple of the parsed value and the remaining text.
        Raises a ValueError if the text cannot be parsed.
        """
        ...


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


def parse_types(cls: type[Dataclass]) -> Iterable[type[Parse]]:
    """
    Returns an iterable containing the types of the elements a given tuple.
    """
    for val in cls.__dataclass_fields__.values():
        if not isinstance(val, Field):
            continue

        yield val.type


class ParseKey(Protocol):
    """
    A class that has a key, representing a full section.
    """

    @classmethod
    def parse_key(cls) -> str:
        """
        The classe's parse key.
        """
        ...


Wrapped = TypeVar("Wrapped")


class Wrap(Generic[Wrapped]):
    """
    Wraps a type to add a custom __repr__ and __str__.

    Forwards all other calls to the wrapped type.
    """

    def __init__(self, value: Wrapped, /) -> None:
        self.value = value

    def __getattr__(self, name: str) -> Any:
        return getattr(self.value, name)

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.value})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.value})"


class String(Wrap[str]):
    ...


class Integer(Wrap[int]):
    @classmethod
    def parse(cls, input: str, /) -> tuple[Integer, str]:
        val, rest = input.split(" ", 1)
        return cls(int(val)), rest


class Double(Wrap[float]):
    ...


class Boolean(Wrap[bool]):
    ...


class Timestamp(Wrap[datetime]):
    ...


class Geolocation(Wrap[Location]):
    ...


Types: TypeAlias = String | Integer | Double | Boolean | Timestamp | Geolocation

InType = TypeVar("InType", contravariant=True)
OutType = TypeVar("OutType", covariant=True)
T = TypeVar("T")


class Vec(Wrap[list[T]]):
    def __repr__(self) -> str:
        return f"Vec([{','.join(repr(val) for val in self.value)}])"


class Map(Wrap[dict[str, T]]):
    def __repr__(self) -> str:
        return f"Map({{{','.join(f'{key}:{repr(val)}' for key, val in self.value.items())}}})"


class Vis(Protocol[InType, OutType]):
    def generate(self, data: InType) -> OutType:
        ...


@dataclass(frozen=True)
class Version:
    major: Integer
    minor: Integer
    patch: Integer

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"Version({self.major}, {self.minor}, {self.patch})"

    @classmethod
    def parse(cls, input: str, /) -> tuple[Version, str]:
        major, rest = Integer.parse(input)
        minor, rest = Integer.parse(rest)
        patch, rest = Integer.parse(rest)
        return cls(major, minor, patch), rest


"""
Service preamble section
"""


class Scope(StrEnum):
    Service = auto()
    Industry = auto()
    Manifacturing = auto()
    Education = auto()
    Healthcare = auto()
    SocialPrograms = auto()
    Government = auto()
    Energy = auto()
    Water = auto()
    Environment = auto()
    Transportation = auto()
    Communication = auto()
    PublicSafety = auto()
    UrbanPlanning = auto()
    Infrastructure = auto()


@dataclass(frozen=True)
class Service:
    name: String
    version: Version
    scope: Scope

    @classmethod
    def parse_key(cls) -> str:
        return ".service"

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.scope})"

    def __repr__(self) -> str:
        return f"Service({self.name}, {self.version}, {self.scope})"


"""
Data section
"""


class Provider(StrEnum):
    Fiware = auto()
    Dataskop = auto()


@dataclass(frozen=True)
class SensorFormat:
    props: Map[Types]

    def __str__(self) -> str:
        return f"SensorFormat({self.props})"

    def __repr__(self) -> str:
        return f"SensorFormat({self.props})"


class SensorType(StrEnum):
    SmartMeter = auto()


@dataclass(frozen=True)
class Sensor:
    type: SensorType
    provider: Provider
    uri: URI
    format: SensorFormat

    def __str__(self) -> str:
        return f"{self.type} ({self.provider}, {self.uri})"

    def __repr__(self) -> str:
        return f"Sensor({self.type}, {self.provider}, {self.uri}, {self.format})"


@dataclass(frozen=True)
class SensorData:
    sensors: Map[Sensor]

    @classmethod
    def parse_key(cls) -> str:
        return ".data"

    def __str__(self) -> str:
        return f"SensorData({self.sensors})"

    def __repr__(self) -> str:
        return f"SensorData({self.sensors})"


"""
Application section
"""


class AppType(StrEnum):
    WebApp = auto()
    MobileApp = auto()
    DesktopApp = auto()
    IoTApp = auto()


class AppLayout(StrEnum):
    SinglePage = auto()
    MultiPage = auto()
    MultiWindow = auto()


class AuthenticationRoles(StrEnum):
    SuperUser = auto()
    Admin = auto()
    User = auto()
    Guest = auto()


@dataclass(frozen=True)
class Authentication:
    name: str
    role: AuthenticationRoles
    default: bool = False

    def __str__(self) -> str:
        return f"{self.name} ({self.role})"

    def __repr__(self) -> str:
        return f"Authentication({self.name}, {self.role}, {self.default})"


class TableGraph:
    ...


class ChartGraph:
    ...


class MapGraph:
    ...


class LineGraph:
    ...


@dataclass(frozen=True)
class TableVis(Generic[T]):
    def generate(self, data: T) -> TableGraph:
        """
        TODO: DEFINE TYPES AND IMPLEMENTATION
        It should take some input data and return a graph type
        """
        ...

    def __str__(self) -> str:
        return "TableVis"

    def __repr__(self) -> str:
        return "TableVis"


@dataclass(frozen=True)
class ChartVis(Generic[T]):
    def generate(self, data: T) -> ChartGraph:
        """
        TODO: DEFINE TYPES AND IMPLEMENTATION
        It should take some input data and return a graph type
        """
        ...

    def __str__(self) -> str:
        return "ChartVis"

    def __repr__(self) -> str:
        return "ChartVis"


@dataclass(frozen=True)
class MapVis(Generic[T]):
    def generate(self, data: T) -> MapGraph:
        """
        TODO: DEFINE TYPES AND IMPLEMENTATION
        It should take some input data and return a graph type
        """
        ...

    def __str__(self) -> str:
        return "MapVis"

    def __repr__(self) -> str:
        return "MapVis"


@dataclass(frozen=True)
class LineVis(Generic[T]):
    def generate(self, data: T) -> LineGraph:
        """
        TODO: DEFINE TYPES AND IMPLEMENTATION
        It should take some input data and return a graph type
        """
        ...

    def __str__(self) -> str:
        return "LineVis"

    def __repr__(self) -> str:
        return "LineVis"


@dataclass(frozen=True)
class Visualizations:
    """
    TODO! Fix this section
    """

    _type: type[Vis[Types, Types]]
    format: Map[type[Types]]

    def __str__(self) -> str:
        return f"{self._type} ({self.format})"

    def __repr__(self) -> str:
        return f"Visualization({self._type}, {self.format})"


@dataclass(frozen=True)
class Application:
    type: AppType
    layout: AppLayout
    graphs: Map[Visualizations]

    @classmethod
    def parse_key(cls) -> str:
        return ".application"

    def __str__(self) -> str:
        return f"Application({self.type}, {self.layout}, {self.graphs})"

    def __repr__(self) -> str:
        return f"Application({self.type}, {self.layout}, {self.graphs})"


"""
Deployment section
"""


class DeploymentType(StrEnum):
    Docker = auto()
    Kubernetes = auto()
    DockerCompose = auto()
    Helm = auto()
    Ansible = auto()
    Terraform = auto()
    CloudFormation = auto()
    Serverless = auto()


@dataclass(frozen=True)
class DeploymentEnv:
    uri: URI
    port: Integer | None
    type: DeploymentType
    credentials: Map[String] | None

    def __str__(self) -> str:
        return f"{self.uri}:{self.port} ({self.type})"

    def __repr__(self) -> str:
        return (
            f"DeploymentEnv({self.uri}, {self.port}, {self.type}, {self.credentials})"
        )


@dataclass(frozen=True)
class Deployment:
    envs: Map[DeploymentEnv]

    @classmethod
    def parse_key(cls) -> str:
        return ".deployment"

    def __str__(self) -> str:
        return f"Deployment({self.envs})"

    def __repr__(self) -> str:
        return f"Deployment({self.envs})"


"""
File section
"""


@dataclass(frozen=True)
class SSDL:
    service: Service
    data: SensorData
    application: Application
    deployment: Deployment

    @classmethod
    def parse_key(cls) -> str:
        return "ssdl"

    def __str__(self) -> str:
        return (
            f"SSDL({self.service}, {self.data}, {self.application}, {self.deployment})"
        )

    def __repr__(self) -> str:
        return (
            f"SSDL({self.service}, {self.data}, {self.application}, {self.deployment})"
        )


if __name__ == "__main__":
    ...

