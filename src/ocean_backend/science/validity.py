"""Scientific validation rules for model-observation comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from ocean_backend.data.observations import Observation


@dataclass(frozen=True)
class ValidityResult:
    """
    Result of validating an observation before comparison.

    This class answers:
        "Is this observation scientifically eligible for comparison?"

    It does NOT validate model support and does NOT perform interpolation.
    """

    valid: bool
    quality_valid: bool
    value_valid: bool
    coordinates_valid: bool
    depth_valid: bool
    time_valid: bool
    variable_valid: bool
    reasons: list[str]


class ObservationValidityValidator:
    """
    Validate an Observation before it enters the comparison pipeline.

    Rules are deliberately conservative:
    - QC FAIL is rejected.
    - UNKNOWN QC is rejected for scientific comparison.
    - Values must be finite.
    - Coordinates must be physically valid.
    - Depth must be finite and non-negative.
    - Time must be a valid datetime.
    - Variable must be non-empty.
    """

    VALID_QC_FLAGS = {"PASS", "SUSPECT", "UNKNOWN", "FAIL"}

    def validate(self, observation: Observation) -> ValidityResult:
        reasons: list[str] = []

        quality_valid = self._validate_quality(
            observation,
            reasons,
        )

        value_valid = self._validate_value(
            observation,
            reasons,
        )

        coordinates_valid = self._validate_coordinates(
            observation,
            reasons,
        )

        depth_valid = self._validate_depth(
            observation,
            reasons,
        )

        time_valid = self._validate_time(
            observation,
            reasons,
        )

        variable_valid = self._validate_variable(
            observation,
            reasons,
        )

        valid = all(
            (
                quality_valid,
                value_valid,
                coordinates_valid,
                depth_valid,
                time_valid,
                variable_valid,
            )
        )

        return ValidityResult(
            valid=valid,
            quality_valid=quality_valid,
            value_valid=value_valid,
            coordinates_valid=coordinates_valid,
            depth_valid=depth_valid,
            time_valid=time_valid,
            variable_valid=variable_valid,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Quality control
    # ------------------------------------------------------------------

    def _validate_quality(
        self,
        observation: Observation,
        reasons: list[str],
    ) -> bool:
        if observation.quality_flag is None:
            reasons.append("Observation quality status is missing.")
            return False

        quality = str(observation.quality_flag).strip().upper()

        if quality not in self.VALID_QC_FLAGS:
            reasons.append(
                f"Unknown observation quality flag: '{observation.quality_flag}'."
            )
            return False

        if quality == "FAIL":
            reasons.append(
                "Observation failed quality control."
            )
            return False

        if quality == "UNKNOWN":
            reasons.append(
                "Observation quality status is unknown."
            )
            return False

        if quality == "SUSPECT":
            reasons.append(
                "Observation has a suspect quality flag."
            )

        return True

    # ------------------------------------------------------------------
    # Value
    # ------------------------------------------------------------------

    def _validate_value(
        self,
        observation: Observation,
        reasons: list[str],
    ) -> bool:
        try:
            value = float(observation.value)
        except (TypeError, ValueError):
            reasons.append("Observation value is not numeric.")
            return False

        if not np.isfinite(value):
            reasons.append(
                "Observation value is NaN or infinite."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Coordinates
    # ------------------------------------------------------------------

    def _validate_coordinates(
        self,
        observation: Observation,
        reasons: list[str],
    ) -> bool:
        try:
            latitude = float(observation.latitude)
            longitude = float(observation.longitude)
        except (TypeError, ValueError):
            reasons.append(
                "Observation coordinates are not numeric."
            )
            return False

        if not np.isfinite(latitude):
            reasons.append(
                "Observation latitude is not finite."
            )
            return False

        if not np.isfinite(longitude):
            reasons.append(
                "Observation longitude is not finite."
            )
            return False

        if not -90.0 <= latitude <= 90.0:
            reasons.append(
                f"Observation latitude {latitude}° is outside [-90°, 90°]."
            )
            return False

        if not -180.0 <= longitude <= 180.0:
            reasons.append(
                f"Observation longitude {longitude}° is outside [-180°, 180°]."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Depth
    # ------------------------------------------------------------------

    def _validate_depth(
        self,
        observation: Observation,
        reasons: list[str],
    ) -> bool:
        try:
            depth = float(observation.depth)
        except (TypeError, ValueError):
            reasons.append(
                "Observation depth is not numeric."
            )
            return False

        if not np.isfinite(depth):
            reasons.append(
                "Observation depth is not finite."
            )
            return False

        if depth < 0:
            reasons.append(
                f"Observation depth {depth} m is invalid."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------

    def _validate_time(
        self,
        observation: Observation,
        reasons: list[str],
    ) -> bool:
        if observation.time is None:
            reasons.append(
                "Observation timestamp is missing."
            )
            return False

        if not isinstance(observation.time, datetime):
            reasons.append(
                "Observation timestamp is not a datetime."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Variable
    # ------------------------------------------------------------------

    def _validate_variable(
        self,
        observation: Observation,
        reasons: list[str],
    ) -> bool:
        if not observation.variable:
            reasons.append(
                "Observation variable is missing."
            )
            return False

        if not str(observation.variable).strip():
            reasons.append(
                "Observation variable cannot be empty."
            )
            return False

        return True