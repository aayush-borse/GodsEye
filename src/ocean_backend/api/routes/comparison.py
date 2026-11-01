"""Model-observation comparison API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ocean_backend.data.argo.adapter import ArgoAdapter
from ocean_backend.data.observation_store import ObservationStore
from ocean_backend.models.schemas import (
    ComparisonEvidence,
    ComparisonRequest,
)
from ocean_backend.services.dataset_runtime import dataset_registry
from ocean_backend.services.model_service import ModelService
from ocean_backend.services.observation_resolver import ObservationResolver
from ocean_backend.services.upload_service import DatasetNotFoundError


router = APIRouter(
    prefix="/comparison",
    tags=["comparison"],
)


# ------------------------------------------------------------------
# PROJECT PATHS
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_DIR = (
    PROJECT_ROOT
    / "src"
    / "ocean_backend"
    / "data"
)

ARGO_PATH = (
    DATA_DIR
    / "argo"
    / "profiles"
    / "1902675_prof.nc"
)


# ------------------------------------------------------------------
# PUBLIC VARIABLE MAPPING
# ------------------------------------------------------------------

OBSERVATION_VARIABLES = {
    "temperature": "thetao",
    "salinity": "so",
    "u": "uo",
    "v": "vo",
    "eastward_velocity": "uo",
    "northward_velocity": "vo",
}


# ------------------------------------------------------------------
# LOAD OPTIONAL ARGO OBSERVATIONS
# ------------------------------------------------------------------

# The source archive can omit large external NetCDF profile files. Keep
# model-only APIs operational in that case and return an explicit empty
# candidate set from observation endpoints instead of failing at import.
if ARGO_PATH.is_file():
    try:
        argo_observations = ArgoAdapter(str(ARGO_PATH)).load_observations()
    except (OSError, ValueError, ImportError):
        argo_observations = []
else:
    argo_observations = []

observation_store = ObservationStore(argo_observations)
observation_resolver = ObservationResolver(observation_store)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def _get_model_service(
    dataset_id: str,
) -> ModelService:
    """
    Create a ModelService for a registered dataset.
    """

    try:
        dataset_path = (
            dataset_registry.get_path(
                dataset_id
            )
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return ModelService(
        dataset_path,
        observation_store=observation_store,
    )


def _normalize_variable(
    variable: str,
) -> str:
    """
    Convert a public variable name into the
    internal observation variable name.
    """

    normalized = str(
        variable
    ).strip()

    try:
        return OBSERVATION_VARIABLES[
            normalized
        ]

    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported variable: "
                f"{normalized}"
            ),
        ) from exc


def _normalize_datetime(
    value: datetime,
) -> datetime:
    """
    Normalize a datetime to a naive UTC datetime.

    The scientific backend currently works with
    timezone-naive dataset timestamps.
    """

    if value.tzinfo is not None:
        return value.astimezone(
            timezone.utc
        ).replace(
            tzinfo=None
        )

    return value


# ------------------------------------------------------------------
# BASIC COMPARISON
# ------------------------------------------------------------------

@router.post(
    "",
    response_model=ComparisonEvidence,
)
def compare(
    request: ComparisonRequest,
    dataset_id: str = Query(...),
) -> ComparisonEvidence:
    """
    Compare a model value with an optional observation.

    If observation_id is supplied, the scientific comparison
    engine resolves the observation and performs collocation.
    """

    try:
        service = _get_model_service(
            dataset_id
        )

        return service.compare(
            request
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ------------------------------------------------------------------
# MODEL REALITY CHECK
# ------------------------------------------------------------------

@router.post(
    "/reality-check",
)
def model_reality_check(
    request: ComparisonRequest,
    dataset_id: str = Query(...),
    limit: int = Query(
        default=3,
        ge=1,
        le=10,
    ),
) -> dict:
    """
    Find nearby comparable observations and compare the model
    against the strongest available candidates.

    Workflow:

        1. Validate the requested model dataset.
        2. Find nearby observations.
        3. Rank observations by comparability.
        4. Compare the model against each candidate.
        5. Return candidates and verified evidence.

    The resolver performs observation discovery.

    ModelService performs the scientific comparison.

    This endpoint itself does not calculate scientific values.
    """

    try:
        # ----------------------------------------------------------
        # 1. Resolve model service
        # ----------------------------------------------------------

        service = _get_model_service(
            dataset_id
        )

        # ----------------------------------------------------------
        # 2. Find nearby observations
        # ----------------------------------------------------------

        candidates_response = (
            observation_resolver.find_nearest(
                latitude=request.latitude,
                longitude=request.longitude,
                depth_m=request.depth_m,
                time=request.time,
                variable=request.variable,
            )
        )

        candidates = (
            candidates_response.candidates[
                :limit
            ]
        )

        # ----------------------------------------------------------
        # 3. Compare model against candidates
        # ----------------------------------------------------------

        comparisons = []

        for candidate in candidates:

            candidate_request = (
                ComparisonRequest(
                    latitude=request.latitude,
                    longitude=request.longitude,
                    depth_m=request.depth_m,
                    time=request.time,
                    variable=request.variable,
                    observation_id=(
                        candidate.observation_id
                    ),
                )
            )

            try:
                evidence = service.compare(
                    candidate_request
                )

                comparisons.append(
                    {
                        "observation": candidate.model_dump(
                            mode="json"
                        ),
                        "comparison": evidence.model_dump(
                            mode="json"
                        ),
                    }
                )

            except ValueError as exc:
                comparisons.append(
                    {
                        "observation": candidate.model_dump(
                            mode="json"
                        ),
                        "comparison": None,
                        "comparison_status": "REJECTED",
                        "comparison_reason": str(exc),
                    }
                )

        # ----------------------------------------------------------
        # 4. Return complete reality-check result
        # ----------------------------------------------------------

        return {
            "requested": request.model_dump(
                mode="json"
            ),
            "dataset_id": dataset_id,
            "variable": request.variable,
            "candidate_count": len(candidates),
            "candidates_checked": len(
                comparisons
            ),
            "results": comparisons,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ------------------------------------------------------------------
# 3D DISAGREEMENT POINTS
# ------------------------------------------------------------------

@router.get(
    "/disagreement",
)
def get_disagreement_points(
    dataset_id: str = Query(...),
    variable: str = Query(...),
    time: datetime = Query(...),

    latitude_min: float | None = Query(
        default=None
    ),
    latitude_max: float | None = Query(
        default=None
    ),
    longitude_min: float | None = Query(
        default=None
    ),
    longitude_max: float | None = Query(
        default=None
    ),

    depth_min: float | None = Query(
        default=None,
        ge=0,
    ),
    depth_max: float | None = Query(
        default=None,
        ge=0,
    ),

    time_tolerance_hours: float = Query(
        default=168.0,
        ge=0,
        le=720,
    ),

    min_confidence: str | None = Query(
        default=None
    ),

    max_points: int = Query(
        default=250,
        ge=1,
        le=1000,
    ),
) -> dict:
    """
    Return observation-supported 3D model-observation
    disagreement points.

    Each returned point represents an actual observation
    that has been collocated with the model.

    This is intentionally NOT a continuous interpolated
    observation-error field.

    The frontend can render these points in 3D and color
    them using the signed model-observation difference.
    """

    # --------------------------------------------------------------
    # Validate variable
    # --------------------------------------------------------------

    observation_variable = _normalize_variable(
        variable
    )

    # --------------------------------------------------------------
    # Validate confidence filter
    # --------------------------------------------------------------

    allowed_confidence = {
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNAVAILABLE",
    }

    if min_confidence is not None:
        min_confidence = (
            min_confidence.strip().upper()
        )

        if (
            min_confidence
            not in allowed_confidence
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid confidence filter. "
                    "Use HIGH, MEDIUM, LOW or "
                    "UNAVAILABLE."
                ),
            )

    # --------------------------------------------------------------
    # Validate geographic/depth ranges
    # --------------------------------------------------------------

    if (
        latitude_min is not None
        and latitude_max is not None
        and latitude_min > latitude_max
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "latitude_min cannot be greater "
                "than latitude_max."
            ),
        )

    if (
        longitude_min is not None
        and longitude_max is not None
        and longitude_min > longitude_max
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "longitude_min cannot be greater "
                "than longitude_max."
            ),
        )

    if (
        depth_min is not None
        and depth_max is not None
        and depth_min > depth_max
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "depth_min cannot be greater "
                "than depth_max."
            ),
        )

    requested_time = _normalize_datetime(
        time
    )

    try:
        # ----------------------------------------------------------
        # Resolve model
        # ----------------------------------------------------------

        service = _get_model_service(
            dataset_id
        )

        # ----------------------------------------------------------
        # Collect candidate observations
        # ----------------------------------------------------------

        candidates = []

        seen = set()

        for observation in (
            observation_store.observations
        ):
            # ------------------------------------------------------
            # Variable filter
            # ------------------------------------------------------

            if (
                str(
                    observation.variable
                ).strip()
                != observation_variable
            ):
                continue

            # ------------------------------------------------------
            # Geographic filter
            # ------------------------------------------------------

            if (
                latitude_min is not None
                and observation.latitude
                < latitude_min
            ):
                continue

            if (
                latitude_max is not None
                and observation.latitude
                > latitude_max
            ):
                continue

            if (
                longitude_min is not None
                and observation.longitude
                < longitude_min
            ):
                continue

            if (
                longitude_max is not None
                and observation.longitude
                > longitude_max
            ):
                continue

            # ------------------------------------------------------
            # Depth filter
            # ------------------------------------------------------

            if (
                depth_min is not None
                and observation.depth
                < depth_min
            ):
                continue

            if (
                depth_max is not None
                and observation.depth
                > depth_max
            ):
                continue

            # ------------------------------------------------------
            # Time filter
            # ------------------------------------------------------

            observation_time = (
                _normalize_datetime(
                    observation.time
                )
            )

            time_difference_hours = abs(
                (
                    observation_time
                    - requested_time
                ).total_seconds()
            ) / 3600.0

            if (
                time_difference_hours
                > time_tolerance_hours
            ):
                continue

            # ------------------------------------------------------
            # Prevent duplicate points
            #
            # A point is uniquely represented by:
            #
            # platform + depth + observation time
            # ------------------------------------------------------

            point_key = (
                str(
                    observation.platform_id
                ),
                round(
                    float(
                        observation.depth
                    ),
                    4,
                ),
                observation_time.isoformat(),
            )

            if point_key in seen:
                continue

            seen.add(
                point_key
            )

            candidates.append(
                observation
            )

        # ----------------------------------------------------------
        # Scientific comparison
        # ----------------------------------------------------------

        results = []

        for observation in candidates:

            # Normalize the timestamp belonging to THIS observation.
            #
            # Do not reuse the timestamp from the candidate-collection
            # loop above, because that could belong to another observation.
            observation_time = _normalize_datetime(
                observation.time
            )

            comparison_request = (
                ComparisonRequest(
                    latitude=float(
                        observation.latitude
                    ),
                    longitude=float(
                        observation.longitude
                    ),
                    depth_m=float(
                        observation.depth
                    ),
                    time=observation_time,
                    variable=variable,
                    observation_id=str(
                        observation.platform_id
                    ),
                )
            )

            try:
                evidence = service.compare(
                    comparison_request
                )

            except ValueError:
                # A candidate observation can exist but still
                # fail model-support or scientific validity checks.
                continues

            if (
                evidence.difference is None
            ):
                continue

            if (
                min_confidence is not None
                and evidence.confidence.upper()
                != min_confidence
            ):
                continue

            difference = float(
                evidence.difference
            )

            results.append(
                {
                    "observation_id": str(
                        observation.platform_id
                    ),
                    "platform_id": str(
                        observation.platform_id
                    ),
                    "latitude": float(
                        observation.latitude
                    ),
                    "longitude": float(
                        observation.longitude
                    ),
                    "depth_m": float(
                        observation.depth
                    ),
                    "time": observation_time.isoformat(),

                    "variable": variable,

                    "model_value": float(
                        evidence.model_value
                    ),
                    "observed_value": float(
                        evidence.observed_value
                    ),

                    "difference": difference,
                    "absolute_difference": abs(
                        difference
                    ),

                    "observation_qc": (
                        evidence.observation_qc
                    ),
                    "confidence": (
                        evidence.confidence
                    ),
                    "confidence_reasons": (
                        evidence.confidence_reasons
                    ),

                    "spatial_distance_km": (
                        evidence.spatial_distance_km
                    ),
                    "depth_difference_m": (
                        evidence.depth_difference_m
                    ),
                    "temporal_difference_hours": (
                        evidence.temporal_difference_hours
                    ),

                    "interpolation": (
                        evidence.interpolation
                    ),
                }
            )

        # ----------------------------------------------------------
        # Keep strongest disagreements first
        # ----------------------------------------------------------

        results.sort(
            key=lambda item: item[
                "absolute_difference"
            ],
            reverse=True,
        )

        # ----------------------------------------------------------
        # Limit response size
        # ----------------------------------------------------------

        results = results[
            :max_points
        ]

        # ----------------------------------------------------------
        # Statistics
        # ----------------------------------------------------------

        differences = [
            item["difference"]
            for item in results
        ]

        absolute_differences = [
            item["absolute_difference"]
            for item in results
        ]

        if differences:
            mean_difference = (
                sum(differences)
                / len(differences)
            )

            mae = (
                sum(
                    absolute_differences
                )
                / len(
                    absolute_differences
                )
            )

            rmse = (
                sum(
                    value * value
                    for value in differences
                )
                / len(differences)
            ) ** 0.5

            minimum_difference = min(
                differences
            )

            maximum_difference = max(
                differences
            )

        else:
            mean_difference = None
            mae = None
            rmse = None
            minimum_difference = None
            maximum_difference = None

        # ----------------------------------------------------------
        # Response
        # ----------------------------------------------------------

        return {
            "dataset_id": dataset_id,
            "variable": variable,
            "requested_time": (
                requested_time.isoformat()
            ),

            "representation": (
                "observation-supported "
                "3D disagreement points"
            ),

            "point_count": len(
                results
            ),

            "statistics": {
                "mean_difference": (
                    mean_difference
                ),
                "mean_absolute_difference": (
                    mae
                ),
                "rmse": rmse,
                "minimum_difference": (
                    minimum_difference
                ),
                "maximum_difference": (
                    maximum_difference
                ),
            },

            "filters": {
                "latitude_min": latitude_min,
                "latitude_max": latitude_max,
                "longitude_min": longitude_min,
                "longitude_max": longitude_max,
                "depth_min": depth_min,
                "depth_max": depth_max,
                "time_tolerance_hours": (
                    time_tolerance_hours
                ),
                "min_confidence": (
                    min_confidence
                ),
            },

            "points": results,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc