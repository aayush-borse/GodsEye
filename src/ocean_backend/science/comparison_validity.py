"""Scientific validity gate for model-observation comparisons."""

from __future__ import annotations

from dataclasses import dataclass

from ocean_backend.data.observations import Observation
from ocean_backend.science.model_support import ModelSupport, ModelSupportValidator
from ocean_backend.science.validity import (
    ObservationValidityValidator,
    ValidityResult,
)


@dataclass(frozen=True)
class ComparisonValidity:
    """
    Combined scientific validity result.

    A comparison is valid only when:
    1. The observation is scientifically eligible.
    2. The model supports the requested comparison point.
    """

    valid: bool
    observation: ValidityResult
    model: ModelSupport
    reasons: list[str]


class ComparisonValidityGate:
    """
    Gatekeeper for model-observation comparisons.

    This class does not interpolate values and does not calculate
    model-observation differences.

    It answers only:

        "Is this comparison scientifically eligible to run?"
    """

    def __init__(
        self,
        model_support_validator: ModelSupportValidator,
        observation_validator: ObservationValidityValidator | None = None,
    ) -> None:
        self.model_support_validator = model_support_validator
        self.observation_validator = (
            observation_validator
            if observation_validator is not None
            else ObservationValidityValidator()
        )

    def validate(
        self,
        *,
        observation: Observation,
        variable: str,
    ) -> ComparisonValidity:
        reasons: list[str] = []

        observation_result = self.observation_validator.validate(
            observation
        )

        if not observation_result.valid:
            reasons.extend(
                f"Observation: {reason}"
                for reason in observation_result.reasons
            )

        model_result = self.model_support_validator.validate(
            latitude=observation.latitude,
            longitude=observation.longitude,
            depth=observation.depth,
            time=observation.time,
            variable=variable,
        )

        if not model_result.supported:
            reasons.extend(
                f"Model: {reason}"
                for reason in model_result.reasons
            )

        return ComparisonValidity(
            valid=(
                observation_result.valid
                and model_result.supported
            ),
            observation=observation_result,
            model=model_result,
            reasons=reasons,
        )

    def validate_model_request(
        self,
        *,
        latitude: float,
        longitude: float,
        depth: float,
        time,
        variable: str,
    ) -> ModelSupport:
        """
        Validate a model-only request.

        No observation is involved in this path.
        """

        return self.model_support_validator.validate(
            latitude=latitude,
            longitude=longitude,
            depth=depth,
            time=time,
            variable=variable,
        )