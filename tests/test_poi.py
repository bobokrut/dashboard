import requests
from src.parsers._parser import get_parsers
from src.parsers import parse


def test_parse_without_errors():
    to_parse = requests.get(
        "https://smart-data-models.github.io/dataModel.PointOfInterest/PointOfInterest/examples/example-normalized.json"
    ).json()

    for k in to_parse.copy():
        if f"parse_{k}" not in get_parsers():
            del to_parse[k]

    parsed = parse([to_parse], to_parse.keys())
    assert parsed
