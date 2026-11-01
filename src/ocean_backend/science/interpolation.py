"""Coordinate-aware interpolation for ocean model fields."""

from datetime import datetime

import numpy as np
import xarray as xr


def linear_time(
    v0: float,
    v1: float,
    alpha: float,
) -> float:
    """
    Linearly interpolate between two values.

    Parameters
    ----------
    v0:
        Value at the first time/position.
    v1:
        Value at the second time/position.
    alpha:
        Interpolation fraction from 0 to 1.
    """

    if not 0.0 <= alpha <= 1.0:
        raise ValueError(
            "Interpolation alpha must be between 0 and 1."
        )

    return float(
        (1.0 - alpha) * v0
        + alpha * v1
    )


def trilinear(
    corners: np.ndarray,
    wx: float,
    wy: float,
    wz: float,
) -> float:
    """
    Trilinearly interpolate an 8-corner voxel.

    Expected corner layout:

        corners[depth, latitude, longitude]
    """

    corners = np.asarray(
        corners,
        dtype=float,
    )

    if corners.shape != (2, 2, 2):
        raise ValueError(
            "Trilinear interpolation requires "
            "exactly 8 corners with shape (2, 2, 2)."
        )

    c00 = (
        corners[0, 0, 0] * (1.0 - wx)
        + corners[0, 0, 1] * wx
    )

    c01 = (
        corners[0, 1, 0] * (1.0 - wx)
        + corners[0, 1, 1] * wx
    )

    c10 = (
        corners[1, 0, 0] * (1.0 - wx)
        + corners[1, 0, 1] * wx
    )

    c11 = (
        corners[1, 1, 0] * (1.0 - wx)
        + corners[1, 1, 1] * wx
    )

    c0 = (
        c00 * (1.0 - wy)
        + c01 * wy
    )

    c1 = (
        c10 * (1.0 - wy)
        + c11 * wy
    )

    return float(
        c0 * (1.0 - wz)
        + c1 * wz
    )


def bilinear_spatial(
    field: np.ndarray,
    latitude: float,
    longitude: float,
) -> float:
    """Bilinearly interpolate a 2D latitude/longitude field."""

    field = np.asarray(
        field,
        dtype=float,
    )

    if field.ndim != 2:
        raise ValueError(
            "Bilinear spatial interpolation requires "
            "a 2D field."
        )

    if field.shape[0] < 2 or field.shape[1] < 2:
        raise ValueError(
            "Bilinear interpolation requires at least "
            "2 points along each spatial axis."
        )

    y = float(latitude)
    x = float(longitude)

    y0 = int(np.floor(y))
    x0 = int(np.floor(x))

    if y0 < 0 or y0 + 1 >= field.shape[0]:
        raise ValueError(
            "Latitude is outside interpolation bounds."
        )

    if x0 < 0 or x0 + 1 >= field.shape[1]:
        raise ValueError(
            "Longitude is outside interpolation bounds."
        )

    wy = y - y0
    wx = x - x0

    value00 = field[y0, x0]
    value01 = field[y0, x0 + 1]
    value10 = field[y0 + 1, x0]
    value11 = field[y0 + 1, x0 + 1]

    return float(
        (
            value00 * (1.0 - wx) * (1.0 - wy)
            + value01 * wx * (1.0 - wy)
            + value10 * (1.0 - wx) * wy
            + value11 * wx * wy
        )
    )


def linear_depth(
    field: np.ndarray,
    depth: float,
) -> float:
    """Linearly interpolate a 1D vertical field."""

    field = np.asarray(
        field,
        dtype=float,
    )

    if field.ndim != 1:
        raise ValueError(
            "Depth interpolation requires a 1D field."
        )

    if len(field) < 2:
        raise ValueError(
            "Depth interpolation requires at least 2 points."
        )

    depths = np.arange(
        len(field),
        dtype=float,
    )

    if (
        depth < depths[0]
        or depth > depths[-1]
    ):
        raise ValueError(
            "Depth is outside interpolation bounds."
        )

    upper = int(
        np.floor(depth)
    )

    if upper >= len(field) - 1:
        return float(
            field[-1]
        )

    alpha = depth - upper

    return linear_time(
        v0=field[upper],
        v1=field[upper + 1],
        alpha=alpha,
    )


def _validate_axis(
    values: np.ndarray,
    name: str,
) -> None:
    """Validate that a coordinate axis is strictly increasing."""

    values = np.asarray(
        values,
        dtype=float,
    )

    if values.ndim != 1:
        raise ValueError(
            f"{name} coordinate must be one-dimensional."
        )

    if len(values) < 2:
        raise ValueError(
            f"{name} coordinate requires at least 2 values."
        )

    differences = np.diff(values)

    if np.any(differences <= 0):
        raise ValueError(
            f"{name} coordinate must be strictly increasing."
        )


def _bracket(
    coordinates: np.ndarray,
    value: float,
) -> tuple[int, int, float]:
    """Find surrounding coordinate indices and interpolation weight."""

    if (
        value < coordinates[0]
        or value > coordinates[-1]
    ):
        raise ValueError(
            "Requested coordinate is outside interpolation bounds."
        )

    upper = int(
        np.searchsorted(
            coordinates,
            value,
            side="right",
        )
    )

    if upper == 0:
        return 0, 0, 0.0

    if upper >= len(coordinates):
        index = len(coordinates) - 1
        return index, index, 0.0

    lower = upper - 1

    denominator = (
        coordinates[upper]
        - coordinates[lower]
    )

    if denominator == 0:
        raise ValueError(
            "Interpolation coordinates cannot contain duplicates."
        )

    weight = (
        value - coordinates[lower]
    ) / denominator

    return (
        lower,
        upper,
        float(weight),
    )


def interpolate_3d(
    field: xr.DataArray,
    latitude: float,
    longitude: float,
    depth: float,
) -> float:
    """
    Trilinearly interpolate a 3D ocean model field.

    The field must contain:

        latitude
        longitude
        depth

    If a time dimension exists, the first time step is used.
    Explicit temporal interpolation is handled by interpolate_4d().
    """

    required_dimensions = {
        "latitude",
        "longitude",
        "depth",
    }

    if not required_dimensions.issubset(
        set(field.dims)
    ):
        raise ValueError(
            "3D interpolation requires latitude, "
            "longitude, and depth dimensions."
        )

    if "time" in field.dims:
        field = field.isel(
            time=0
        )

    field = field.transpose(
        "depth",
        "latitude",
        "longitude",
    )

    latitudes = np.asarray(
        field["latitude"].values,
        dtype=float,
    )

    longitudes = np.asarray(
        field["longitude"].values,
        dtype=float,
    )

    depths = np.asarray(
        field["depth"].values,
        dtype=float,
    )

    _validate_axis(
        latitudes,
        "latitude",
    )

    _validate_axis(
        longitudes,
        "longitude",
    )

    _validate_axis(
        depths,
        "depth",
    )

    lat0, lat1, wy = _bracket(
        latitudes,
        float(latitude),
    )

    lon0, lon1, wx = _bracket(
        longitudes,
        float(longitude),
    )

    depth0, depth1, wz = _bracket(
        depths,
        float(depth),
    )

    values = np.asarray(
        field.values,
        dtype=float,
    )

    corners = np.array(
        [
            [
                [
                    values[
                        depth_index,
                        latitude_index,
                        longitude_index,
                    ]
                    for longitude_index in (
                        [lon0, lon1]
                    )
                ]
                for latitude_index in (
                    [lat0, lat1]
                )
            ]
            for depth_index in (
                [depth0, depth1]
            )
        ],
        dtype=float,
    )

    if np.any(
        ~np.isfinite(corners)
    ):
        raise ValueError(
            "Cannot interpolate because the surrounding "
            "model grid contains NaN or infinite values."
        )

    return trilinear(
        corners,
        wx=wx,
        wy=wy,
        wz=wz,
    )


def interpolate_4d(
    field: xr.DataArray,
    latitude: float,
    longitude: float,
    depth: float,
    time: np.datetime64,
) -> float:
    """
    Interpolate an ocean model field in space, depth, and time.

    Spatial interpolation:
        trilinear

    Temporal interpolation:
        linear
    """

    required_dimensions = {
        "time",
        "latitude",
        "longitude",
        "depth",
    }

    if not required_dimensions.issubset(
        set(field.dims)
    ):
        raise ValueError(
            "4D interpolation requires time, latitude, "
            "longitude, and depth dimensions."
        )

    field = field.transpose(
        "time",
        "depth",
        "latitude",
        "longitude",
    )

    times = field["time"].values

    if len(times) == 0:
        raise ValueError(
            "Model field contains no time steps."
        )

    if len(times) == 1:

        if (
            np.datetime64(
                time,
                "ns",
            )
            != times[0]
        ):
            raise ValueError(
                "Temporal interpolation requires at least "
                "two model time steps."
            )

        return interpolate_3d(
            field.isel(
                time=0
            ),
            latitude,
            longitude,
            depth,
        )

    times_ns = (
        times
        .astype("datetime64[ns]")
        .astype(np.int64)
    )

    target_ns = (
        np.datetime64(
            time,
            "ns",
        )
        .astype(np.int64)
    )

    if (
        target_ns < times_ns[0]
        or target_ns > times_ns[-1]
    ):
        raise ValueError(
            "Requested time is outside model time bounds."
        )

    upper = int(
        np.searchsorted(
            times_ns,
            target_ns,
            side="right",
        )
    )

    if upper == 0:
        return interpolate_3d(
            field.isel(
                time=0
            ),
            latitude,
            longitude,
            depth,
        )

    if upper >= len(times_ns):
        return interpolate_3d(
            field.isel(
                time=-1
            ),
            latitude,
            longitude,
            depth,
        )

    lower = upper - 1

    denominator = (
        times_ns[upper]
        - times_ns[lower]
    )

    if denominator == 0:
        raise ValueError(
            "Model time coordinates cannot contain duplicates."
        )

    alpha = (
        target_ns
        - times_ns[lower]
    ) / denominator

    value0 = interpolate_3d(
        field.isel(
            time=lower
        ),
        latitude,
        longitude,
        depth,
    )

    value1 = interpolate_3d(
        field.isel(
            time=upper
        ),
        latitude,
        longitude,
        depth,
    )

    return linear_time(
        v0=value0,
        v1=value1,
        alpha=float(alpha),
    )


def nearest_model_grid_point(
    dataset: xr.Dataset,
    latitude: float,
    longitude: float,
) -> tuple[float, float, float]:
    """
    Find the nearest model latitude/longitude grid point.

    Returns:

        nearest_latitude,
        nearest_longitude,
        distance_km
    """

    latitudes = np.asarray(
        dataset["latitude"].values,
        dtype=float,
    )

    longitudes = np.asarray(
        dataset["longitude"].values,
        dtype=float,
    )

    if latitudes.ndim != 1:
        raise ValueError(
            "Nearest-grid lookup currently requires "
            "one-dimensional latitude coordinates."
        )

    if longitudes.ndim != 1:
        raise ValueError(
            "Nearest-grid lookup currently requires "
            "one-dimensional longitude coordinates."
        )

    nearest_latitude = float(
        latitudes[
            np.argmin(
                np.abs(
                    latitudes
                    - float(latitude)
                )
            )
        ]
    )

    nearest_longitude = float(
        longitudes[
            np.argmin(
                np.abs(
                    longitudes
                    - float(longitude)
                )
            )
        ]
    )

    distance = _haversine_distance_km(
        latitude,
        longitude,
        nearest_latitude,
        nearest_longitude,
    )

    return (
        nearest_latitude,
        nearest_longitude,
        distance,
    )


def nearest_model_time(
    dataset: xr.Dataset,
    time: datetime | np.datetime64,
) -> tuple[np.datetime64, float]:
    """
    Find the model output time closest to an observation time.

    Returns:

        nearest_model_time,
        absolute_difference_hours
    """

    times = dataset["time"].values

    if len(times) == 0:
        raise ValueError(
            "Model dataset contains no time coordinates."
        )

    target = np.datetime64(
        time,
        "ns",
    )

    differences = np.abs(
        times
        .astype("datetime64[ns]")
        .astype(np.int64)
        - target.astype(np.int64)
    )

    nearest_index = int(
        np.argmin(
            differences
        )
    )

    nearest_time = times[
        nearest_index
    ]

    difference_hours = (
        float(
            differences[
                nearest_index
            ]
        )
        / 3_600_000_000_000.0
    )

    return (
        nearest_time,
        difference_hours,
    )


def _haversine_distance_km(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """Calculate great-circle distance between two coordinates."""

    earth_radius_km = 6371.0

    lat1 = np.deg2rad(
        latitude1
    )

    lat2 = np.deg2rad(
        latitude2
    )

    delta_lat = np.deg2rad(
        latitude2
        - latitude1
    )

    delta_lon = np.deg2rad(
        longitude2
        - longitude1
    )

    value = (
        np.sin(
            delta_lat / 2.0
        )
        ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(
            delta_lon / 2.0
        )
        ** 2
    )

    value = np.clip(
        value,
        0.0,
        1.0,
    )

    central_angle = (
        2.0
        * np.arcsin(
            np.sqrt(value)
        )
    )

    return float(
        earth_radius_km
        * central_angle
    )