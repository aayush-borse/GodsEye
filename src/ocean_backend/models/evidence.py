"""Evidence packet models for scientific model-observation validation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceModel(BaseModel):
    """Model-side evidence."""

    value: float
    dataset_id: str
    interpolation: str


class EvidenceObservation(BaseModel):
    """Observation-side evidence."""

    value: float
    observation_id: str
    source: str
    quality_control: str


class EvidenceDifference(BaseModel):
    """Model-observation difference."""

    value: float
    absolute: float


class EvidenceCollocation(BaseModel):
    """Spatial, depth and temporal collocation metadata."""

    horizontal_distance_km: float
    depth_difference_m: float
    time_difference_hours: float


class EvidenceConfidence(BaseModel):
    """Explainable confidence information."""

    level: str
    reasons: list[str] = Field(
        default_factory=list
    )


class EvidenceProvenance(BaseModel):
    """Traceability information for the comparison."""

    model_dataset: str
    observation_source: str
    interpolation_method: str


class EvidencePacket(BaseModel):
    """
    Complete scientific evidence packet.

    This object is designed to be consumed by the frontend,
    AI narrator and future evidence export functionality.
    """

    observation_id: str
    variable: str

    model: EvidenceModel

    observation: EvidenceObservation

    difference: EvidenceDifference

    collocation: EvidenceCollocation

    confidence: EvidenceConfidence

    provenance: EvidenceProvenance