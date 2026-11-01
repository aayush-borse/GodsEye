"""API schemas for ocean observations and scientific comparisons."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ==============================================================
# OBSERVATION SCHEMAS
# ==============================================================


class ObservationResponse(BaseModel):
    """Single observation returned by the API."""

    observation_id: str
    platform_id: str

    latitude: float
    longitude: float
    depth_m: float
    time: datetime

    variable: str
    value: float

    quality_flag: str = "UNKNOWN"

    cycle_number: int | None = None
    value_source: str | None = None
    data_mode: str | None = None


class ObservationProfileResponse(BaseModel):
    """Vertical profile for an observation platform."""

    observation_id: str
    platform_id: str

    latitude: float
    longitude: float

    time: datetime | None = None

    variable: str

    depths_m: list[float]
    values: list[float]

    quality_flags: list[str] = Field(
        default_factory=list
    )


# ==============================================================
# NEAREST OBSERVATION
# ==============================================================


class ObservationCandidate(BaseModel):
    """
    Ranked observation candidate for model-observation
    collocation.

    The ranking is transparent so the frontend can explain
    why an observation was selected.
    """

    observation_id: str
    platform_id: str

    latitude: float
    longitude: float
    depth_m: float
    time: datetime

    variable: str
    value: float

    quality_flag: str

    horizontal_distance_km: float
    depth_difference_m: float
    time_difference_hours: float

    comparability_score: float

    ranking_reasons: list[str] = Field(
        default_factory=list
    )


class NearestObservationResponse(BaseModel):
    """Ranked observations near a requested ocean location."""

    requested_latitude: float
    requested_longitude: float
    requested_depth_m: float
    requested_time: datetime

    variable: str

    candidates: list[ObservationCandidate]

    count: int


# ==============================================================
# MODEL / OBSERVATION COMPARISON
# ==============================================================


class ComparisonRequest(BaseModel):
    """Request for model-only or model-observation comparison."""

    latitude: float
    longitude: float
    depth_m: float

    time: datetime

    variable: str

    observation_id: str | None = None


class Coordinate4D(BaseModel):
    """Legacy coordinate-only request shape retained for narrator clients."""

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    depth_m: float = Field(ge=0.0)
    time: datetime


class ComparisonEvidence(BaseModel):
    """Scientific evidence produced by the comparison engine."""

    variable: str

    # Coordinate4D is accepted for backwards compatibility with the
    # original evidence narrator interface; current API flows use the
    # richer ComparisonRequest including the variable.
    requested: ComparisonRequest | Coordinate4D

    model_value: float

    observed_value: float | None = None

    difference: float | None = None

    spatial_distance_km: float | None = None

    temporal_difference_hours: float | None = None

    depth_difference_m: float | None = None

    observation_qc: str = "UNKNOWN"

    interpolation: str

    confidence: str

    confidence_reasons: list[str] = Field(
        default_factory=list
    )


# ==============================================================
# GENERIC DATA RESPONSE
# ==============================================================


class GenericDataResponse(BaseModel):
    """Generic JSON-safe data response."""

    data: dict[str, Any]