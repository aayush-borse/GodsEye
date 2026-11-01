from datetime import datetime, timezone

import pytest

from ocean_backend.ai.observation_resolver import ObservationResolver
from ocean_backend.data.observation_store import ObservationStore
from ocean_backend.data.observations import Observation


def make_observation(
    platform_id: str = "1902675_1",
) -> Observation:
    return Observation(
        platform_id=platform_id,
        latitude=-8.0,
        longitude=77.0,
        depth=100.0,
        time=datetime(
            2024,
            1,
            17,
            tzinfo=timezone.utc,
        ),
        variable="temperature",
        value=20.5,
        quality_flag="PASS",
    )


def test_resolves_base_platform_id():
    observation = make_observation()

    store = ObservationStore(
        [observation]
    )

    resolver = ObservationResolver(
        store
    )

    result = resolver.resolve(
        "1902675"
    )

    assert result is observation


def test_resolves_exact_profile_id():
    observation = make_observation(
        "1902675_25"
    )

    store = ObservationStore(
        [observation]
    )

    resolver = ObservationResolver(
        store
    )

    result = resolver.resolve(
        "1902675_25"
    )

    assert result is observation


def test_unknown_observation_raises_error():
    store = ObservationStore([])

    resolver = ObservationResolver(
        store
    )

    with pytest.raises(
        ValueError,
        match="Observation '9999999' was not found",
    ):
        resolver.resolve(
            "9999999"
        )