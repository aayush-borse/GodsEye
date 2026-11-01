"""Oceanographic diagnostics.

Diagnostics are added only with explicit definitions, units,
assumptions and tests.
"""

from __future__ import annotations

import numpy as np


def vertical_temperature_gradient(
    temperature,
    depth,
):
    """
    Compute dT/dz along the depth axis.

    Depth is expected to increase downward in metres.
    """

    temperature = np.asarray(
        temperature,
        dtype=float,
    )

    depth = np.asarray(
        depth,
        dtype=float,
    )

    if temperature.shape[-1] != depth.size:
        raise ValueError(
            "depth must match the last axis of temperature"
        )

    return np.gradient(
        temperature,
        depth,
        axis=-1,
    )


def thermocline_depth(
    temperature,
    depth,
):
    """
    Estimate thermocline depth from a vertical temperature profile.

    The thermocline is estimated as the depth where the magnitude
    of the vertical temperature gradient is strongest.

    Parameters
    ----------
    temperature:
        One-dimensional temperature profile.

    depth:
        One-dimensional depth coordinate in metres.

    Returns
    -------
    dict
        Thermocline depth, gradient and profile index.

    Notes
    -----
    This is a diagnostic estimate, not a claim that the water column
    contains a classical thermocline under every oceanographic
    condition.
    """

    temperature = np.asarray(
        temperature,
        dtype=float,
    ).reshape(-1)

    depth = np.asarray(
        depth,
        dtype=float,
    ).reshape(-1)

    if temperature.size != depth.size:
        raise ValueError(
            "temperature and depth must contain the same number of values"
        )

    if temperature.size < 2:
        raise ValueError(
            "At least two depth levels are required"
        )

    valid = (
        np.isfinite(temperature)
        & np.isfinite(depth)
    )

    if np.count_nonzero(valid) < 2:
        raise ValueError(
            "Temperature profile does not contain enough valid values"
        )

    valid_temperature = temperature[valid]
    valid_depth = depth[valid]

    # Depth must be ordered for a meaningful vertical gradient.
    order = np.argsort(valid_depth)

    valid_temperature = valid_temperature[order]
    valid_depth = valid_depth[order]

    gradient = vertical_temperature_gradient(
        valid_temperature,
        valid_depth,
    )

    strongest_index = int(
        np.argmax(
            np.abs(gradient)
        )
    )

    return {
        "depth": float(
            valid_depth[strongest_index]
        ),
        "gradient": float(
            gradient[strongest_index]
        ),
        "gradient_magnitude": float(
            abs(gradient[strongest_index])
        ),
        "index": strongest_index,
    }