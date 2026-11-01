import pytest

from ocean_backend.science.geo import distance_km


def test_distance_same_point():
    result = distance_km(
        12.5,
        70.5,
        12.5,
        70.5,
    )

    assert result == pytest.approx(0.0)


def test_distance_one_degree_latitude():
    result = distance_km(
        0.0,
        0.0,
        1.0,
        0.0,
    )

    assert result == pytest.approx(111.2, abs=0.2)