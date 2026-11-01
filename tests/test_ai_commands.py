from datetime import datetime

import pytest
from pydantic import ValidationError

from ocean_backend.ai.commands import AICommandType
from ocean_backend.ai.schemas import AICommand


def test_show_profile_command():
    command = AICommand(
        command=AICommandType.SHOW_PROFILE,
        variable="temperature",
        location={
            "latitude": 12.5,
            "longitude": 70.5,
        },
        time=datetime(2026, 6, 22, 12),
    )

    assert command.command == AICommandType.SHOW_PROFILE
    assert command.variable == "temperature"
    assert command.location is not None
    assert command.location.latitude == 12.5
    assert command.location.longitude == 70.5


def test_compare_model_observation_command():
    command = AICommand(
        command=AICommandType.COMPARE_MODEL_OBSERVATION,
        variable="temperature",
        observation_id="ARGO_TEST_001",
    )

    assert command.command == AICommandType.COMPARE_MODEL_OBSERVATION
    assert command.observation_id == "ARGO_TEST_001"


def test_invalid_variable_is_rejected():
    with pytest.raises(ValidationError):
        AICommand(
            command=AICommandType.SHOW_VOLUME,
            variable="pressure",
        )


def test_invalid_latitude_is_rejected():
    with pytest.raises(ValidationError):
        AICommand(
            command=AICommandType.SHOW_VOLUME,
            location={
                "latitude": 120.0,
                "longitude": 70.0,
            },
        )


def test_invalid_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        AICommand(
            command=AICommandType.SHOW_VOLUME,
            random_command="DELETE_DATA",
        )