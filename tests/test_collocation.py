import pytest

from ocean_backend.models.collocation import CollocationResult


def test_collocation_result_creation():
    result = CollocationResult(
        platform_id="ARGO_TEST_001",
        variable="thetao",
        observed_value=18.91,
        model_value=19.04,
        difference=0.13,
        distance_km=1.8,
        depth_difference_m=0.0,
        time_difference_hours=12.0,
        confidence="HIGH",
        interpolation_method="trilinear",
        quality_flag="PASS",
        confidence_reasons=["Observation passed quality control."]
    )

    assert result.platform_id == "ARGO_TEST_001"
    assert result.variable == "thetao"

    assert result.observed_value == pytest.approx(18.91)
    assert result.model_value == pytest.approx(19.04)
    assert result.difference == pytest.approx(0.13)

    assert result.distance_km == pytest.approx(1.8)
    assert result.depth_difference_m == pytest.approx(0.0)
    assert result.time_difference_hours == pytest.approx(12.0)
    assert result.confidence == "HIGH"
    assert result.interpolation_method == "trilinear"
    assert result.quality_flag == "PASS"