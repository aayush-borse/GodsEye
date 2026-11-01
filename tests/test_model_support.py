from datetime import datetime

import numpy as np
import xarray as xr

from ocean_backend.science.model_support import ModelSupportValidator


def make_dataset() -> xr.Dataset:
    return xr.Dataset(
        {
            "temperature": (
                ("time", "depth", "lat", "lon"),
                np.ones((2, 3, 2, 2)),
            ),
            "salinity": (
                ("time", "depth", "lat", "lon"),
                np.ones((2, 3, 2, 2)) * 35,
            ),
        },
        coords={
            "time": np.array(
                [
                    "2024-01-17T00:00:00",
                    "2024-01-18T00:00:00",
                ],
                dtype="datetime64[ns]",
            ),
            "depth": [0.0, 100.0, 200.0],
            "lat": [-10.0, -5.0],
            "lon": [75.0, 80.0],
        },
    )


def test_valid_request_is_supported() -> None:
    dataset = make_dataset()
    validator = ModelSupportValidator(dataset)

    result = validator.validate(
        latitude=-8.0,
        longitude=77.0,
        depth=100.0,
        time=datetime(2024, 1, 17, 12),
        variable="temperature",
    )

    assert result.supported is True
    assert result.variable_supported is True
    assert result.latitude_supported is True
    assert result.longitude_supported is True
    assert result.depth_supported is True
    assert result.time_supported is True
    assert result.data_available is True
    assert result.reasons == []


def test_unknown_variable_is_rejected() -> None:
    validator = ModelSupportValidator(make_dataset())

    result = validator.validate(
        latitude=-8.0,
        longitude=77.0,
        depth=100.0,
        time=datetime(2024, 1, 17),
        variable="oxygen",
    )

    assert result.supported is False
    assert result.variable_supported is False
    assert any("oxygen" in reason for reason in result.reasons)


def test_depth_outside_model_range_is_rejected() -> None:
    validator = ModelSupportValidator(make_dataset())

    result = validator.validate(
        latitude=-8.0,
        longitude=77.0,
        depth=500.0,
        time=datetime(2024, 1, 17),
        variable="temperature",
    )

    assert result.supported is False
    assert result.depth_supported is False
    assert any("500.0" in reason for reason in result.reasons)


def test_location_outside_model_domain_is_rejected() -> None:
    validator = ModelSupportValidator(make_dataset())

    result = validator.validate(
        latitude=20.0,
        longitude=77.0,
        depth=100.0,
        time=datetime(2024, 1, 17),
        variable="temperature",
    )

    assert result.supported is False
    assert result.latitude_supported is False


def test_time_outside_model_range_is_rejected() -> None:
    validator = ModelSupportValidator(make_dataset())

    result = validator.validate(
        latitude=-8.0,
        longitude=77.0,
        depth=100.0,
        time=datetime(2025, 1, 17),
        variable="temperature",
    )

    assert result.supported is False
    assert result.time_supported is False


def test_negative_depth_is_rejected() -> None:
    validator = ModelSupportValidator(make_dataset())

    result = validator.validate(
        latitude=-8.0,
        longitude=77.0,
        depth=-10.0,
        time=datetime(2024, 1, 17),
        variable="temperature",
    )

    assert result.supported is False
    assert result.depth_supported is False