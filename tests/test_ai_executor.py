import pytest

from ocean_backend.ai.commands import CommandType, OceanCommand
from ocean_backend.ai.executor import OceanCommandExecutor
from ocean_backend.ai.validator import CommandValidationError


def test_executor_returns_volume_action():
    command = OceanCommand(command=CommandType.SHOW_VOLUME, dataset_id="io-model-4d", variable="temperature")
    result = OceanCommandExecutor().execute(command)
    assert result == {
        "command": "SHOW_VOLUME",
        "status": "ready",
        "action": "show_volume",
        "dataset_id": "io-model-4d",
        "variable": "temperature",
    }


def test_executor_rejects_incomplete_command():
    with pytest.raises(CommandValidationError):
        OceanCommandExecutor().execute(OceanCommand(command=CommandType.SHOW_VOLUME))


def test_executor_returns_observation_action():
    result = OceanCommandExecutor().execute(OceanCommand(command=CommandType.SHOW_OBSERVATIONS))
    assert result["action"] == "show_observations"
