"""Observation API routes."""

from __future__ import annotations

import math
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ocean_backend.data.argo.adapter import ArgoAdapter
from ocean_backend.data.observation_store import ObservationStore


router = APIRouter(
    prefix="/observations",
    tags=["observations"],
)


# --------------------------------------------------------------
# ARGO DATA
# --------------------------------------------------------------

# Resolve the optional sample profile relative to this module, never the
# process working directory. Source archives may intentionally omit large
# scientific data files; in that case the API remains available and returns
# an empty observation collection rather than failing during module import.
ARGO_PATH = (
    Path(__file__).resolve().parents[3]
    / "ocean_backend"
    / "data"
    / "argo"
    / "profiles"
    / "1902675_prof.nc"
)


def _load_bundled_observations():
    if not ARGO_PATH.is_file():
        return []
    try:
        return ArgoAdapter(str(ARGO_PATH)).load_observations()
    except (OSError, ValueError, ImportError):
        # Missing optional NetCDF engines or an invalid optional sample file
        # should not prevent unrelated upload/model APIs from starting.
        return []


observation_store = ObservationStore(_load_bundled_observations())


# --------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------

def _safe_value(value):
    """Convert a value into a JSON-safe Python value."""

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, float) and not math.isfinite(value):
        return None

    return value


def _observation_dict(observation):
    """Convert an observation object into a lightweight API object."""

    return {
        "id": observation.platform_id,
        "latitude": _safe_value(observation.latitude),
        "longitude": _safe_value(observation.longitude),
        "depth": _safe_value(observation.depth),
        "time": str(observation.time),
        "variable": observation.variable,
        "value": _safe_value(observation.value),
        "qc": observation.quality_flag,
    }


def _distance_score(
    observation,
    latitude: float,
    longitude: float,
    depth: float | None,
):
    """
    Calculate a simple comparison score.

    Horizontal distance is approximated in kilometres.

    Depth difference is included when a target depth is supplied.
    """

    lat_difference = (
        float(observation.latitude)
        - latitude
    )

    lon_difference = (
        float(observation.longitude)
        - longitude
    )

    # Approximate kilometre conversion.
    horizontal_km = math.sqrt(
        (lat_difference * 111.0) ** 2
        + (
            lon_difference
            * 111.0
            * math.cos(
                math.radians(latitude)
            )
        ) ** 2
    )

    if depth is None:
        depth_difference = 0.0
    else:
        depth_difference = abs(
            float(observation.depth)
            - depth
        )

    # Keep the score transparent.
    #
    # One kilometre horizontally is treated as one score unit.
    # Depth is converted to kilometres before being added.
    score = (
        horizontal_km
        + depth_difference / 1000.0
    )

    return (
        score,
        horizontal_km,
        depth_difference,
    )


# --------------------------------------------------------------
# LIST OBSERVATIONS
# --------------------------------------------------------------

@router.get("")
def get_observations(
    limit: int = Query(
        100,
        ge=1,
        le=1000,
    ),
):
    """Return lightweight observations for map rendering."""

    observations = observation_store.observations

    results = []

    for observation in observations[:limit]:
        results.append(
            _observation_dict(
                observation
            )
        )

    return {
        "count": len(results),
        "observations": results,
    }


# --------------------------------------------------------------
# NEAREST OBSERVATIONS
# --------------------------------------------------------------

@router.get("/nearest")
def get_nearest_observations(
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
    ),
    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
    ),
    depth: float | None = Query(
        None,
        ge=0,
    ),
    variable: str | None = Query(
        None,
    ),
    limit: int = Query(
        5,
        ge=1,
        le=50,
    ),
    max_distance_km: float | None = Query(
        None,
        gt=0,
    ),
):
    """
    Find observations nearest to a geographic location.

    Results are ranked using horizontal distance and, when supplied,
    depth difference.

    This endpoint is intended for the Model Reality Check workflow.
    """

    observations = (
        observation_store.observations
    )

    normalized_variable = (
        variable.strip().lower()
        if variable
        else None
    )

    candidates = []

    for observation in observations:

        # ------------------------------------------------------
        # Variable filter
        # ------------------------------------------------------

        if normalized_variable:

            observation_variable = (
                str(observation.variable)
                .strip()
                .lower()
            )

            aliases = {
                "temperature": {
                    "temperature",
                    "thetao",
                },
                "salinity": {
                    "salinity",
                    "so",
                },
                "u": {
                    "u",
                    "uo",
                },
                "v": {
                    "v",
                    "vo",
                },
            }

            accepted = aliases.get(
                normalized_variable,
                {normalized_variable},
            )

            if observation_variable not in accepted:
                continue

        # ------------------------------------------------------
        # Calculate proximity
        # ------------------------------------------------------

        (
            score,
            horizontal_km,
            depth_difference,
        ) = _distance_score(
            observation=observation,
            latitude=latitude,
            longitude=longitude,
            depth=depth,
        )

        # ------------------------------------------------------
        # Optional distance limit
        # ------------------------------------------------------

        if (
            max_distance_km is not None
            and horizontal_km > max_distance_km
        ):
            continue

        candidates.append(
            (
                score,
                horizontal_km,
                depth_difference,
                observation,
            )
        )

    # ----------------------------------------------------------
    # Nearest first
    # ----------------------------------------------------------

    candidates.sort(
        key=lambda item: item[0]
    )

    selected = candidates[
        :limit
    ]

    results = []

    for (
        score,
        horizontal_km,
        depth_difference,
        observation,
    ) in selected:

        result = _observation_dict(
            observation
        )

        result.update(
            {
                "horizontal_distance_km": (
                    round(
                        horizontal_km,
                        4,
                    )
                ),
                "depth_difference_m": (
                    round(
                        depth_difference,
                        4,
                    )
                ),
                "proximity_score": round(
                    score,
                    4,
                ),
            }
        )

        results.append(
            result
        )

    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "depth": depth,
            "variable": variable,
        },
        "count": len(results),
        "observations": results,
    }


# --------------------------------------------------------------
# SINGLE OBSERVATION
# --------------------------------------------------------------

@router.get("/{observation_id}")
def get_observation(
    observation_id: str,
):
    """Return one observation."""

    observations = (
        observation_store.observations
    )

    for observation in observations:

        if observation.platform_id == observation_id:

            return _observation_dict(
                observation
            )

    raise HTTPException(
        status_code=404,
        detail=(
            f"Observation '{observation_id}' "
            "was not found."
        ),
    )


# --------------------------------------------------------------
# OBSERVATION PROFILE
# --------------------------------------------------------------

@router.get("/{observation_id}/profile")
def get_observation_profile(
    observation_id: str,
):
    """
    Return the vertical profile associated with an observation.

    The frontend can use this to display depth versus variable value
    after a user selects an Argo marker.
    """

    observations = (
        observation_store.observations
    )

    matching = [
        observation
        for observation in observations
        if observation.platform_id == observation_id
    ]

    if not matching:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Observation '{observation_id}' "
                "was not found."
            ),
        )

    target = matching[0]

    profile = []

    for observation in observations:

        if (
            observation.latitude
            == target.latitude
            and observation.longitude
            == target.longitude
        ):
            profile.append(
                {
                    "id": observation.platform_id,
                    "depth": _safe_value(
                        observation.depth
                    ),
                    "value": _safe_value(
                        observation.value
                    ),
                    "variable": observation.variable,
                    "time": str(
                        observation.time
                    ),
                    "qc": observation.quality_flag,
                }
            )

    profile.sort(
        key=lambda item: (
            item["depth"]
            if item["depth"] is not None
            else float("inf")
        )
    )

    return {
        "observation_id": observation_id,
        "latitude": _safe_value(
            target.latitude
        ),
        "longitude": _safe_value(
            target.longitude
        ),
        "variable": target.variable,
        "profile": profile,
    }