from datetime import datetime

from ocean_backend.data.observations import Observation


def test_observation_creation():
    observation = Observation(
        platform_id="ARGO_TEST_001",
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=datetime(2026, 6, 23),
        variable="thetao",
        value=18.91,
        quality_flag="PASS",
    )

    assert observation.platform_id == "ARGO_TEST_001"
    assert observation.latitude == 12.5
    assert observation.longitude == 70.5
    assert observation.depth == 150.0
    assert observation.variable == "thetao"
    assert observation.value == 18.91
    assert observation.quality_flag == "PASS"