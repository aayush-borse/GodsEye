def depth_difference_m(
    depth1: float,
    depth2: float,
) -> float:
    """
    Calculate the absolute depth difference between two measurements.

    Returns:
        Difference in meters.
    """
    return abs(depth1 - depth2)