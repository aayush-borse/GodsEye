"""Scientific model-observation collocation models."""

from dataclasses import dataclass


@dataclass
class CollocationResult:
    """Result of collocating an observation with a model field."""

    platform_id: str
    variable: str

    observed_value: float
    model_value: float
    difference: float

    distance_km: float
    depth_difference_m: float
    time_difference_hours: float

    confidence: str

    interpolation_method: str

    quality_flag: str

    confidence_reasons: list[str]