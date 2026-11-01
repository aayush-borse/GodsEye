from datetime import datetime

import pytest

from ocean_backend.science.time import time_difference_hours


def test_time_difference_same_time():
    result = time_difference_hours(
        datetime(2026, 6, 22, 12),
        datetime(2026, 6, 22, 12),
    )

    assert result == pytest.approx(0.0)


def test_time_difference_twelve_hours():
    result = time_difference_hours(
        datetime(2026, 6, 22, 12),
        datetime(2026, 6, 23, 0),
    )

    assert result == pytest.approx(12.0)


def test_time_difference_is_absolute():
    result = time_difference_hours(
        datetime(2026, 6, 23, 0),
        datetime(2026, 6, 22, 12),
    )

    assert result == pytest.approx(12.0)