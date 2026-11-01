from datetime import datetime

from ocean_backend.data.observations import Observation
from ocean_backend.data.observation_store import ObservationStore


def test_observation_store_finds_observation():
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

    result = store.get_by_id("ARGO_TEST_001")

    assert result == observation