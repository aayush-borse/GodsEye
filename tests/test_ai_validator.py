import pytest

from ocean_backend.ai.commands import CommandType, OceanCommand
from ocean_backend.ai.validator import CommandValidationError, validate_command


def test_valid_volume_command():
    command = OceanCommand(command=CommandType.SHOW_VOLUME, dataset_id="io-model-4d", variable="temperature")
    assert validate_command(command) == command


def test_volume_requires_dataset():
    with pytest.raises(CommandValidationError, match="requires dataset_id"):
        validate_command(OceanCommand(command=CommandType.SHOW_VOLUME, variable="temperature"))


def test_profile_requires_observation():
    with pytest.raises(CommandValidationError, match="requires observation_id"):
        validate_command(OceanCommand(command=CommandType.SHOW_PROFILE))


def test_comparison_requires_dataset_observation_and_variable():
    with pytest.raises(CommandValidationError, match="requires dataset_id"):
        validate_command(OceanCommand(command=CommandType.COMPARE_MODEL_OBSERVATION))


def test_rejects_unsupported_variable():
    with pytest.raises(CommandValidationError, match="Unsupported variable"):
        validate_command(OceanCommand(command=CommandType.FILTER_BY_VARIABLE, dataset_id="d1", variable="pressure"))


def test_depth_range_must_be_ordered():
    with pytest.raises(CommandValidationError, match="depth_min cannot be greater"):
        validate_command(OceanCommand(command=CommandType.FILTER_BY_DEPTH, dataset_id="d1", depth_min=500, depth_max=100))
