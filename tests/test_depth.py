import pytest

from ocean_backend.science.depth import depth_difference_m


def test_depth_difference_same_depth():
    result = depth_difference_m(150.0, 150.0)

    assert result == pytest.approx(0.0)


def test_depth_difference():
    result = depth_difference_m(150.0, 175.0)

    assert result == pytest.approx(25.0)


def test_depth_difference_is_absolute():
    result = depth_difference_m(175.0, 150.0)

    assert result == pytest.approx(25.0)