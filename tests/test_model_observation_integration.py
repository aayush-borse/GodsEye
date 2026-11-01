from datetime import datetime
import numpy as np
import xarray as xr
import pytest

from ocean_backend.data.observations import Observation
from ocean_backend.science.comparison import model_observation_difference
from ocean_backend.science.interpolation import interpolate_4d

def test_model_observation_integration():
    ds = xr.open_dataset(
        "src/ocean_backend/data/model_4d.nc"
    )

    observation = Observation(
        platform_id="TEST_001",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="thetao",
        value=18.91,
        quality_flag="PASS",
    )

    model_value = interpolate_4d(
    ds["thetao"],
    observation.latitude,
    observation.longitude,
    observation.depth,
    np.datetime64(observation.time),
    )

    difference = model_observation_difference(
        model_value,
        observation.value,
    )

    ds.close()

    assert model_value == pytest.approx(24.941710472106937)
    assert difference == pytest.approx(
    24.941710472106937 - 18.91
    )
    assert np.isfinite(model_value)
    assert -3.0 <= model_value <= 40.0