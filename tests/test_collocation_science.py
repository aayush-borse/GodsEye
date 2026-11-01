from datetime import datetime

import pytest

from ocean_backend.data.observations import Observation
from ocean_backend.science.collocation import build_collocation_result


def test_build_collocation_result():
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

    result = build_collocation_result(
        observation=observation,
        model_value=19.041767673312027,
        model_latitude=12.5,
        model_longitude=70.5,
        model_depth=150.0,
        model_time=datetime(2026, 6, 22, 12),
        interpolation_method="trilinear + linear temporal",
    )

    assert result.platform_id == "ARGO_TEST_001"
    assert result.variable == "thetao"

    assert result.observed_value == pytest.approx(18.91)
    assert result.model_value == pytest.approx(19.041767673312027)

    assert result.difference == pytest.approx(
        0.131767673312027
    )

    assert result.distance_km == pytest.approx(0.0)
    assert result.depth_difference_m == pytest.approx(0.0)
    assert result.time_difference_hours == pytest.approx(0.0)

    assert result.interpolation_method == "trilinear + linear temporal"

    assert result.confidence_reasons == [
        "Observation passed quality control.",
        "Small spatial separation.",
        "Small depth separation.",
        "Small temporal separation.",
    ]


def test_collocation_rejects_invalid_quality_flag():
    observation = Observation(
        platform_id="ARGO_TEST_002",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="thetao",
        value=18.91,
        quality_flag="INVALID",
    )

    with pytest.raises(ValueError):
        build_collocation_result(
            observation=observation,
            model_value=19.04,
            model_latitude=12.5,
            model_longitude=70.5,
            model_depth=150.0,
            model_time=datetime(2026, 6, 22, 12),
            interpolation_method="trilinear",
        )
        
        
        
        
def test_collocation_normalizes_quality_flag():
    observation = Observation(
        platform_id="ARGO_TEST_003",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="thetao",
        value=18.91,
        quality_flag="pass",
    )

    result = build_collocation_result(
        observation=observation,
        model_value=19.04,
        model_latitude=12.5,
        model_longitude=70.5,
        model_depth=150.0,
        model_time=datetime(2026, 6, 22, 12),
        interpolation_method="trilinear",
    )

    assert result.quality_flag == "PASS"
    
    
def test_failed_observation_gets_low_confidence():
    observation = Observation(
        platform_id="ARGO_TEST_004",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 22, 12),
        variable="thetao",
        value=18.91,
        quality_flag="FAIL",
    )

    result = build_collocation_result(
        observation=observation,
        model_value=19.04,
        model_latitude=12.5,
        model_longitude=70.5,
        model_depth=150.0,
        model_time=datetime(2026, 6, 22, 12),
        interpolation_method="trilinear",
    )

    assert result.quality_flag == "FAIL"
    assert result.confidence == "LOW"
    assert "Observation failed quality control." in result.confidence_reasons