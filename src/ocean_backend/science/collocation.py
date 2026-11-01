"""Scientific model-observation collocation logic."""

from ocean_backend.data.observations import Observation
from ocean_backend.models.collocation import CollocationResult
from ocean_backend.science.confidence import calculate_confidence
from ocean_backend.science.geo import distance_km
from ocean_backend.science.time import time_difference_hours


def _normalize_quality_flag(quality_flag: str) -> str:
    """Normalize an observation quality flag."""

    if quality_flag is None:
        return "UNKNOWN"

    normalized = str(quality_flag).strip().upper()

    if normalized in {"PASS", "SUSPECT", "FAIL", "UNKNOWN"}:
        return normalized

    raise ValueError(
        f"Invalid observation quality flag: {quality_flag}"
    )


def build_collocation_result(
    observation: Observation,
    model_value: float,
    model_latitude: float,
    model_longitude: float,
    model_depth: float,
    model_time,
    interpolation_method: str,
) -> CollocationResult:
    """
    Build a scientifically traceable model-observation comparison.

    The model value is assumed to have already been interpolated to
    the requested observation location, depth, and time.

    This function calculates:

    - model-observation difference
    - spatial separation
    - depth separation
    - temporal separation
    - evidence confidence
    - confidence reasons
    """

    quality_flag = _normalize_quality_flag(
        observation.quality_flag
    )

    difference = (
        float(model_value)
        - float(observation.value)
    )

    spatial_distance = distance_km(
        observation.latitude,
        observation.longitude,
        model_latitude,
        model_longitude,
    )

    depth_difference = abs(
        float(observation.depth)
        - float(model_depth)
    )

    temporal_difference = time_difference_hours(
        observation.time,
        model_time,
    )

    confidence, confidence_reasons = calculate_confidence(
        quality_flag=quality_flag,
        distance_km=spatial_distance,
        depth_difference_m=depth_difference,
        time_difference_hours=temporal_difference,
    )

    return CollocationResult(
        platform_id=observation.platform_id,
        variable=observation.variable,
        observed_value=float(observation.value),
        model_value=float(model_value),
        difference=difference,
        distance_km=float(spatial_distance),
        depth_difference_m=float(depth_difference),
        time_difference_hours=float(temporal_difference),
        confidence=confidence,
        interpolation_method=interpolation_method,
        quality_flag=quality_flag,
        confidence_reasons=confidence_reasons,
    )