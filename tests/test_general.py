import datetime

import pytest

from src.parser._parser import ParserException, _parse_address, _parse_location, parse


def test_parse_location_point():
    data = {
        "value": {
            "type": "Point",
            "coordinates": [-3.712247222222222, 40.423852777777775],
        }
    }
    assert _parse_location(data) == (40.423852777777775, -3.712247222222222)


def test_parse_location_line_string():
    data = {
        "value": {
            "type": "LineString",
            "coordinates": [
                [-3.712247222222222, 40.423852777777775],
                [-3.712347222222222, 40.423952777777775],
            ],
        }
    }
    expected = [
        (40.423852777777775, -3.712247222222222),
        (40.423952777777775, -3.712347222222222),
    ]
    assert _parse_location(data) == expected


def test_parse_location_not_implemented():
    data = {
        "value": {
            "type": "UnsupportedType",
            "coordinates": [-3.712247222222222, 40.423852777777775],
        }
    }
    with pytest.raises(NotImplementedError):
        _parse_location(data)


def test_parse_address():
    data = {
        "value": {
            "streetAddress": "Street",
            "postalCode": "12345",
            "addressLocality": "City",
            "addressRegion": "Region",
            "addressCountry": "Country",
        }
    }
    assert _parse_address(data) == "Street, 12345, City, Region, Country"


def test_parse_invalid_key():
    data = [{"testKey": {"value": {"type": "Point", "coordinates": [0, 0]}}}]
    keys = ["testKey"]

    with pytest.raises(ParserException):
        parse(data, keys)


def test_parse_valid_data():
    data = [
        {
            "id": "Alert:1",
            "dateCreated": {"type": "DateTime", "value": "2019-06-06T12:06:06"},
            "category": {"value": "traffic"},
            "location": {
                "type": "geo:json",
                "value": {
                    "type": "Point",
                    "coordinates": [-3.712247222222222, 40.423852777777775],
                },
            },
        }
    ]
    keys = ["id", "dateCreated", "category", "location"]

    expected = [
        [
            "Alert:1",
            datetime.datetime(2019, 6, 6, 12, 6, 6),
            "traffic",
            (40.423852777777775, -3.712247222222222),
        ]
    ]

    assert parse(data, keys) == expected
