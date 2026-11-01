from datetime import datetime

import numpy as np


def _to_datetime(value) -> datetime:
    """Convert supported datetime values to a Python datetime."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, np.datetime64):
        if np.isnat(value):
            raise ValueError("Datetime value cannot be NaT.")

        return value.astype("datetime64[us]").tolist()

    raise TypeError(
        f"Unsupported datetime type: {type(value).__name__}"
    )


def time_difference_hours(
    time1,
    time2,
) -> float:
    """
    Calculate the absolute time difference between two timestamps.

    Supports both Python datetime and NumPy datetime64 values.

    Returns:
        Difference in hours.
    """
    dt1 = _to_datetime(time1)
    dt2 = _to_datetime(time2)

    difference = abs(dt1 - dt2)

    return difference.total_seconds() / 3600.0