import pytest

from ocean_backend.ai.commands import CommandType
from ocean_backend.ai.parser import OceanCommandParser


def test_parse_temperature_profile():
    command = OceanCommandParser().parse("Show temperature profile for Argo 1902675")
    assert command.command == CommandType.SHOW_PROFILE
    assert command.variable == "temperature"
    assert command.observation_id == "1902675"


def test_parse_salinity_profile():
    command = OceanCommandParser().parse("Show salinity profile for float 1902675")
    assert command.command == CommandType.SHOW_PROFILE
    assert command.variable == "salinity"


def test_parse_argo_comparison_before_generic_observation_intent():
    command = OceanCommandParser().parse(
        "Compare Argo 1902675 with the model temperature",
        dataset_id="io-model-4d",
    )
    assert command.command == CommandType.COMPARE_MODEL_OBSERVATION
    assert command.variable == "temperature"
    assert command.observation_id == "1902675"


def test_parse_observations():
    command = OceanCommandParser().parse("Show ocean observations")
    assert command.command == CommandType.SHOW_OBSERVATIONS


def test_parse_thermocline():
    command = OceanCommandParser().parse("Show the thermocline", dataset_id="io-model-4d")
    assert command.command == CommandType.SHOW_THERMOCLINE


def test_parse_volume():
    command = OceanCommandParser().parse(
        "Show the 3D temperature volume", dataset_id="io-model-4d"
    )
    assert command.command == CommandType.SHOW_VOLUME
    assert command.variable == "temperature"


def test_parser_rejects_empty_and_unknown_input():
    parser = OceanCommandParser()
    with pytest.raises(ValueError):
        parser.parse("")
    with pytest.raises(ValueError):
        parser.parse("Tell me a joke")
