from datetime import datetime

import pytest

from ocean_backend.models.schemas import ComparisonRequest
from ocean_backend.services.model_service import ModelService
from ocean_backend.data.observations import Observation
from ocean_backend.data.observation_store import ObservationStore

def test_model_service_returns_temperature_comparison():
    service = ModelService(
        "src/ocean_backend/data/model_4d.nc"
    )

    request = ComparisonRequest(
        latitude=12.5,
        longitude=70.5,
        depth_m=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="temperature",
    )

    result = service.compare(request)

    assert result.variable == "temperature"
    assert result.model_value == pytest.approx(
        24.941710472106937
    )
   #observation lookup 
def test_model_service_compares_with_observation():
    observation = Observation(
        platform_id="ARGO_TEST_001",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="thetao",
        value=18.91,
        quality_flag="PASS",
    )

    store = ObservationStore([observation])

    service = ModelService(
        "src/ocean_backend/data/model_4d.nc",
        observation_store=store,
    )

    request = ComparisonRequest(
        latitude=12.5,
        longitude=70.5,
        depth_m=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="temperature",
        observation_id="ARGO_TEST_001",
    )

    result = service.compare(request)

    assert result.model_value == pytest.approx(24.941710472106937)
    assert result.observed_value == pytest.approx(18.91)
    assert result.difference == pytest.approx(6.031710472106937)
    assert result.observation_qc == "PASS"
    assert result.confidence == "LOW"
    assert result.confidence_reasons
    assert result.interpolation == "trilinear + linear temporal"
    assert result.spatial_distance_km == pytest.approx(283.28404559399496)
    assert result.temporal_difference_hours == pytest.approx(0.0)
    assert result.depth_difference_m == pytest.approx(0.0)
    
def test_model_service_rejects_missing_observation():
    service = ModelService(
        "src/ocean_backend/data/model_4d.nc",
        observation_store=ObservationStore(),
    )

    request = ComparisonRequest(
        latitude=12.5,
        longitude=70.5,
        depth_m=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="temperature",
        observation_id="DOES_NOT_EXIST",
    )

    with pytest.raises(ValueError, match="Observation not found"):
        service.compare(request)
        
        
def test_model_service_uses_observation_coordinates_for_collocation():
    observation = Observation(
        platform_id="ARGO_TEST_002",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="thetao",
        value=18.91,
        quality_flag="PASS",
    )

    store = ObservationStore([observation])

    service = ModelService(
        "src/ocean_backend/data/model_4d.nc",
        observation_store=store,
    )

    request = ComparisonRequest(
        latitude=15.0,
        longitude=73.0,
        depth_m=300.0,
        time=datetime(2026, 6, 23, 12),
        variable="temperature",
        observation_id="ARGO_TEST_002",
    )

    result = service.compare(request)

    assert result.model_value == pytest.approx(24.941710472106937)
    assert result.observed_value == pytest.approx(18.91)

    assert result.spatial_distance_km == pytest.approx(283.28404559399496)
    assert result.depth_difference_m == pytest.approx(150.0)
    assert result.temporal_difference_hours == pytest.approx(0.0)


def test_model_service_rejects_variable_mismatch():
    observation = Observation(
        platform_id="ARGO_SALINITY_001",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="so",
        value=35.2,
        quality_flag="PASS",
    )

    store = ObservationStore([observation])

    service = ModelService(
        "src/ocean_backend/data/model_4d.nc",
        observation_store=store,
    )

    request = ComparisonRequest(
        latitude=12.5,
        longitude=70.5,
        depth_m=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="temperature",
        observation_id="ARGO_SALINITY_001",
    )

    with pytest.raises(
        ValueError,
        match="does not match requested variable",
    ):
        service.compare(request)