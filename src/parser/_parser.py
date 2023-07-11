import re
from collections import namedtuple
from types import FunctionType
from typing import Any, NewType, TypeAlias

from dateutil.parser import parse as parse_date

Url = NewType("Url", str)
Position = namedtuple("Position", ["lat", "lon"])

FiwareJson: TypeAlias = list[dict[str, Any]]


class ParserException(Exception):
    """Exception raised when a parser is not found"""


class NotNeeded(Exception):
    """Exception raised when a value is not needed."""

    pass


#########################################################
#                      Location                         #
#########################################################


def _parse_location(
    location: dict[str, Any]
) -> Position | list[Position] | list[list[Position]]:
    match location["value"]["type"]:
        case "Point":
            return Position(
                lon=location["value"]["coordinates"][0],
                lat=location["value"]["coordinates"][1],
            )
        case "LineString":
            return [
                Position(lon=lon, lat=lat)
                for lon, lat in location["value"]["coordinates"]
            ]
        case "Polygon":
            return [
                Position(lon=lon, lat=lat)
                for lon, lat in location["value"]["coordinates"][0]
            ]
        case "MultiPoint":
            return [
                Position(lon=lon, lat=lat)
                for lon, lat in location["value"]["coordinates"]
            ]
        case "MultiLineString":
            return [
                [Position(lon=p[0], lat=p[1]) for p in line_string]
                for line_string in location["value"]["coordinates"]
            ]
        case _:
            raise NotImplementedError


def _parse_address(address: dict[str, Any]) -> str:
    return_address = ""
    address = address["value"]

    if "streetAddress" in address:
        return_address += (
            f"{address['streetAddress']}, "
            if "streerNr" not in address
            else f"{address['streetAddress']} {address['streetNr']}, "
        )

    if "postalCode" in address:
        return_address += address["postalCode"] + ", "

    if "addressLocality" in address:
        return_address += address["addressLocality"] + ", "

    if "addressRegion" in address:
        return_address += address["addressRegion"] + ", "

    if "addressCountry" in address:
        return_address += address["addressCountry"]

    return return_address


def get_parsers() -> dict[str, FunctionType]:
    return {
        name: obj for name, obj in globals().items() if isinstance(obj, FunctionType)
    }


def __parse_old(data: FiwareJson, keys: list[str]) -> list[list[Any]]:
    to_return = []
    parsers = get_parsers()
    try:
        for d in data:
            to_return.append([parsers[f"parse_{key}"](d[key]) for key in keys])

        return to_return

    except KeyError as e:
        raise ParserException(f"Parser for {e} not found")


def _parse_value(value: Any) -> Any:
    if re.fullmatch(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b", value):
        return parse_date(value)

    return value


def _parse(data: FiwareJson, keys: list[str]) -> list[list[Any]]:
    to_return = []
    parsers = get_parsers()

    for d in data:
        l = []
        for key in keys:
            item = d[key]

            if (
                f"_parse_{key}" in parsers
            ):  # If there is a custom parser to parse an object
                l.append(parsers[f"_parse_{key}"](item))

            elif isinstance(item, str):
                l.append(item)

            elif (
                isinstance(item, dict)
                and "value" in item
                and not isinstance(item["value"], dict)
            ):
                l.append(_parse_value(item["value"]))

            else:
                raise ParserException(f"Parser for {key} not found\nValue: {item}")

        to_return.append(l)

    return to_return


def parse(data: FiwareJson, keys: list[str]) -> list[list[Any]]:
    """Parses data from the Fiware with the given data keys"""
    return _parse(data, keys)
