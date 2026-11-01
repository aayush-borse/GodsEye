from datetime import datetime

from ocean_backend.data.observations import Observation
from ocean_backend.science.validity import ObservationValidityValidator


def make_observation(**overrides) -> Observation:
    values = {
        "platform_id": "1902675_1",
        "latitude": -8.98,
        "longitude": 76.95,
        "depth": 150.0,
        "time": datetime(2024, 1, 17, 14, 9, 49),
        "variable": "temperature",
        "value": 17.197,
        "quality_flag": "PASS",
    }

    values.update(overrides)

    return Observation(**values)


def test_valid_observation() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(make_observation())

    assert result.valid is True
    assert result.quality_valid is True
    assert result.value_valid is True
    assert result.coordinates_valid is True
    assert result.depth_valid is True
    assert result.time_valid is True
    assert result.variable_valid is True
    assert result.reasons == []


def test_fail_qc_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(quality_flag="FAIL")
    )

    assert result.valid is False
    assert result.quality_valid is False
    assert "failed quality control" in result.reasons[0].lower()


def test_unknown_qc_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(quality_flag="UNKNOWN")
    )

    assert result.valid is False
    assert result.quality_valid is False


def test_suspect_qc_is_allowed_but_recorded() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(quality_flag="SUSPECT")
    )

    assert result.valid is True
    assert result.quality_valid is True
    assert any("suspect" in reason.lower() for reason in result.reasons)


def test_nan_value_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(value=float("nan"))
    )

    assert result.valid is False
    assert result.value_valid is False


def test_infinite_value_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(value=float("inf"))
    )

    assert result.valid is False
    assert result.value_valid is False


def test_invalid_latitude_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(latitude=95.0)
    )

    assert result.valid is False
    assert result.coordinates_valid is False


def test_invalid_longitude_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(longitude=200.0)
    )

    assert result.valid is False
    assert result.coordinates_valid is False


def test_negative_depth_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(depth=-10.0)
    )

    assert result.valid is False
    assert result.depth_valid is False


def test_missing_time_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(time=None)
    )

    assert result.valid is False
    assert result.time_valid is False


def test_missing_variable_is_rejected() -> None:
    validator = ObservationValidityValidator()

    result = validator.validate(
        make_observation(variable="")
    )

    assert result.valid is False
    assert result.variable_valid is False