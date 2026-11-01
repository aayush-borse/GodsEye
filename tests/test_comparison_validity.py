from datetime import datetime

import numpy as np
import xarray as xr

from ocean_backend.data.observations import Observation
from ocean_backend.science.comparison_validity import (
    ComparisonValidityGate,
)
from ocean_backend.science.model_support import (
    ModelSupportValidator,
)


def make_dataset() -> xr.Dataset:
    return xr.Dataset(
        {
            "thetao": (
                ("time", "depth", "latitude", "longitude"),
                np.ones((2, 3, 2, 2)),
            )
        },
        coords={
            "time": np.array(
                [
                    "2024-01-17T00:00:00",
                    "2024-01-18T00:00:00",
                ],
                dtype="datetime64[ns]",
            ),
            "depth": [0.0, 50.0, 100.0],
            "latitude": [-10.0, -8.0],
            "longitude": [76.0, 78.0],
        },
    )


def make_observation(
    *,
    quality_flag: str = "PASS",
    value: float = 20.0,
    depth: float = 50.0,
) -> Observation:
    return Observation(
        platform_id="1902675_1",
        latitude=-8.0,
        longitude=78.0,
        depth=depth,
        time=datetime(2024, 1, 17),
        variable="thetao",
        value=value,
        quality_flag=quality_flag,
    )


def test_valid_comparison():
    dataset = make_dataset()

    gate = ComparisonValidityGate(
        model_support_validator=ModelSupportValidator(dataset)
    )

    result = gate.validate(
        observation=make_observation(),
        variable="thetao",
    )

    assert result.valid is True
    assert result.observation.valid is True
    assert result.model.supported is True


def test_failed_observation_qc_is_rejected():
    dataset = make_dataset()

    gate = ComparisonValidityGate(
        model_support_validator=ModelSupportValidator(dataset)
    )

    result = gate.validate(
        observation=make_observation(
            quality_flag="FAIL"
        ),
        variable="thetao",
    )

    assert result.valid is False
    assert result.observation.valid is False


def test_unknown_observation_qc_is_rejected():
    dataset = make_dataset()

    gate = ComparisonValidityGate(
        model_support_validator=ModelSupportValidator(dataset)
    )

    result = gate.validate(
        observation=make_observation(
            quality_flag="UNKNOWN"
        ),
        variable="thetao",
    )

    assert result.valid is False


def test_nan_observation_is_rejected():
    dataset = make_dataset()

    gate = ComparisonValidityGate(
        model_support_validator=ModelSupportValidator(dataset)
    )

    result = gate.validate(
        observation=make_observation(
            value=float("nan")
        ),
        variable="thetao",
    )

    assert result.valid is False


def test_observation_outside_model_depth_is_rejected():
    dataset = make_dataset()

    gate = ComparisonValidityGate(
        model_support_validator=ModelSupportValidator(dataset)
    )

    result = gate.validate(
        observation=make_observation(
            depth=200.0
        ),
        variable="thetao",
    )

    assert result.valid is False
    assert result.model.depth_supported is False


def test_observation_outside_model_time_is_rejected():
    dataset = make_dataset()

    gate = ComparisonValidityGate(
        model_support_validator=ModelSupportValidator(dataset)
    )

    observation = make_observation()

    observation.time = datetime(2025, 1, 1)

    result = gate.validate(
        observation=observation,
        variable="thetao",
    )

    assert result.valid is False
    assert result.model.time_supported is False