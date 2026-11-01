"""Diagnostic and model-data access API routes."""

from __future__ import annotations

import math

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from ocean_backend.science.diagnostics import thermocline_depth
from ocean_backend.services.dataset_runtime import dataset_registry
from ocean_backend.services.upload_service import DatasetNotFoundError


router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
)


# --------------------------------------------------------------
# Supported variable names
# --------------------------------------------------------------

VARIABLES = {
    "temperature": "thetao",
    "salinity": "so",
    "u": "uo",
    "v": "vo",
    "eastward_velocity": "uo",
    "northward_velocity": "vo",
}


# --------------------------------------------------------------
# Safety limit
# --------------------------------------------------------------

MAX_VALUES = 100_000


def _json_safe(value):
    """Convert NumPy/Python values into JSON-safe values."""

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, list):
        return [
            _json_safe(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


# --------------------------------------------------------------
# Existing volume diagnostic
# --------------------------------------------------------------

@router.get("/volume")
def get_volume(
    dataset_id: str = Query(
        ...,
        description="ID returned by POST /datasets/upload",
    ),
    variable: str = Query(
        "temperature",
        description=(
            "Variable to retrieve: temperature, salinity, u or v."
        ),
    ),
    stride: int = Query(
        4,
        ge=1,
        le=20,
        description=(
            "Sampling stride applied to depth, latitude and "
            "longitude dimensions."
        ),
    ),
):
    """Return a bounded 3D volume for visualization."""

    try:
        dataset = dataset_registry.get(
            dataset_id
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    variable_key = str(variable).strip().lower()

    if variable_key not in VARIABLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported variable '{variable}'. "
                f"Supported variables: "
                f"{', '.join(VARIABLES.keys())}."
            ),
        )

    model_variable = VARIABLES[variable_key]

    if model_variable not in dataset.data_vars:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Variable '{model_variable}' "
                "is not available in this dataset."
            ),
        )

    data = dataset[model_variable]

    selection = {}

    for dimension in data.dims:

        dimension_lower = dimension.lower()

        if dimension_lower in {
            "depth",
            "latitude",
            "longitude",
            "lat",
            "lon",
        }:
            selection[dimension] = slice(
                None,
                None,
                stride,
            )

    sampled = data.isel(
        selection
    )

    value_count = sampled.size

    if value_count > MAX_VALUES:
        raise HTTPException(
            status_code=413,
            detail={
                "message": (
                    "Requested volume is too large. "
                    "Increase the stride."
                ),
                "values": int(value_count),
                "maximum_values": MAX_VALUES,
                "suggested_stride": min(
                    stride + 1,
                    20,
                ),
            },
        )

    values = _json_safe(
        sampled.values.tolist()
    )

    coordinates = {}

    for dimension in sampled.dims:

        if dimension not in dataset.coords:
            continue

        coordinate = dataset.coords[
            dimension
        ]

        if coordinate.dims == (dimension,):

            coordinate = coordinate.isel(
                {
                    dimension: slice(
                        None,
                        None,
                        stride,
                    )
                }
            )

        coordinates[dimension] = _json_safe(
            coordinate.values.tolist()
        )

    return {
        "dataset_id": dataset_id,
        "variable": variable_key,
        "model_variable": model_variable,
        "dimensions": list(sampled.dims),
        "shape": [
            int(size)
            for size in sampled.shape
        ],
        "stride": stride,
        "value_count": int(value_count),
        "coordinates": coordinates,
        "values": values,
    }


# --------------------------------------------------------------
# Thermocline diagnostic
# --------------------------------------------------------------

@router.get("/thermocline")
def get_thermocline(
    dataset_id: str = Query(
        ...,
        description="ID returned by POST /datasets/upload",
    ),
    latitude: float = Query(
        ...,
        description="Target latitude in degrees.",
    ),
    longitude: float = Query(
        ...,
        description="Target longitude in degrees.",
    ),
    time_index: int = Query(
        0,
        ge=0,
        description="Time index to analyse.",
    ),
):
    """
    Estimate thermocline depth at a geographic location.

    The backend selects the nearest model grid point and analyses
    the vertical temperature profile there.
    """

    # ----------------------------------------------------------
    # Get dataset
    # ----------------------------------------------------------

    try:
        dataset = dataset_registry.get(
            dataset_id
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    # ----------------------------------------------------------
    # Validate required variables and coordinates
    # ----------------------------------------------------------

    if "thetao" not in dataset.data_vars:
        raise HTTPException(
            status_code=400,
            detail="Temperature variable 'thetao' is not available.",
        )

    required_coordinates = (
        "latitude",
        "longitude",
        "depth",
    )

    missing = [
        coordinate
        for coordinate in required_coordinates
        if coordinate not in dataset.coords
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Dataset is missing required coordinates.",
                "missing": missing,
            },
        )

    temperature = dataset[
        "thetao"
    ]

    # ----------------------------------------------------------
    # Select time
    # ----------------------------------------------------------

    if "time" in temperature.dims:

        time_size = temperature.sizes[
            "time"
        ]

        if time_index >= time_size:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"time_index {time_index} is outside the "
                    f"available range 0-{time_size - 1}."
                ),
            )

        temperature = temperature.isel(
            time=time_index
        )

    # ----------------------------------------------------------
    # Select nearest geographic grid point.
    # ----------------------------------------------------------

    try:
        profile = temperature.sel(
            latitude=latitude,
            longitude=longitude,
            method="nearest",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to select a model profile at the "
                "requested location."
            ),
        ) from exc

    if "depth" not in profile.dims:
        raise HTTPException(
            status_code=400,
            detail=(
                "Temperature variable does not contain "
                "a depth dimension."
            ),
        )

    # ----------------------------------------------------------
    # Get actual selected grid coordinates.
    # ----------------------------------------------------------

    selected_latitude = float(
        np.asarray(
            profile.coords["latitude"].values
        )
    )

    selected_longitude = float(
        np.asarray(
            profile.coords["longitude"].values
        )
    )

    depth_values = np.asarray(
        profile.coords["depth"].values,
        dtype=float,
    )

    temperature_values = np.asarray(
        profile.values,
        dtype=float,
    )

    # ----------------------------------------------------------
    # Calculate thermocline.
    # ----------------------------------------------------------

    try:
        result = thermocline_depth(
            temperature=temperature_values,
            depth=depth_values,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ----------------------------------------------------------
    # Return both the diagnostic and enough provenance to explain
    # what was actually analysed.
    # ----------------------------------------------------------

    return {
        "dataset_id": dataset_id,
        "variable": "thetao",
        "time_index": time_index,
        "requested_location": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "selected_model_location": {
            "latitude": selected_latitude,
            "longitude": selected_longitude,
        },
        "thermocline": {
            "depth_m": result["depth"],
            "gradient_degC_per_m": result["gradient"],
            "gradient_magnitude_degC_per_m": (
                result["gradient_magnitude"]
            ),
            "profile_index": result["index"],
        },
        "profile": {
            "depth_m": [
                float(value)
                for value in depth_values
            ],
            "temperature_degC": _json_safe(
                temperature_values.tolist()
            ),
        },
    }