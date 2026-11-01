"""Nearest-observation resolution for model-observation analysis."""

from __future__ import annotations

from datetime import datetime

from ocean_backend.data.observation_store import ObservationStore
from ocean_backend.models.schemas import (
    NearestObservationResponse,
    ObservationCandidate,
)


class ObservationResolver:
    """
    Find observations that are physically comparable to a
    requested model location.

    This service does NOT calculate model values.

    It only answers:

        "Which real observations are closest to this
         location, depth, time and variable?"
    """

    # ----------------------------------------------------------
    # Ranking limits
    # ----------------------------------------------------------

    MAX_HORIZONTAL_DISTANCE_KM = 500.0
    MAX_DEPTH_DIFFERENCE_M = 500.0
    MAX_TIME_DIFFERENCE_HOURS = 168.0

    def __init__(
        self,
        observation_store: ObservationStore,
    ) -> None:
        self.observation_store = observation_store

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------

    def find_nearest(
        self,
        *,
        latitude: float,
        longitude: float,
        depth_m: float,
        time: datetime,
        variable: str,
        limit: int = 5,
    ) -> NearestObservationResponse:
        """
        Find the most comparable observations.

        Ranking considers:

        1. horizontal distance
        2. depth difference
        3. temporal difference
        4. observation quality

        No model calculation happens here.
        """

        if limit < 1:
            raise ValueError(
                "limit must be at least 1."
            )

        if limit > 50:
            raise ValueError(
                "limit cannot be greater than 50."
            )

        normalized_variable = (
            self._normalize_variable(variable)
        )

        candidates: list[
            ObservationCandidate
        ] = []

        for observation in (
            self.observation_store.observations
        ):

            if not self._variable_matches(
                observation.variable,
                normalized_variable,
            ):
                continue

            horizontal_distance = (
                self._haversine_distance(
                    latitude,
                    longitude,
                    observation.latitude,
                    observation.longitude,
                )
            )

            depth_difference = abs(
                float(depth_m)
                - float(observation.depth)
            )

            time_difference = (
                self._time_difference_hours(
                    time,
                    observation.time,
                )
            )

            if horizontal_distance > (
                self.MAX_HORIZONTAL_DISTANCE_KM
            ):
                continue

            if depth_difference > (
                self.MAX_DEPTH_DIFFERENCE_M
            ):
                continue

            if time_difference > (
                self.MAX_TIME_DIFFERENCE_HOURS
            ):
                continue

            quality = (
                str(
                    observation.quality_flag
                )
                .strip()
                .upper()
            )

            score = self._comparability_score(
                horizontal_distance_km=(
                    horizontal_distance
                ),
                depth_difference_m=(
                    depth_difference
                ),
                time_difference_hours=(
                    time_difference
                ),
                quality_flag=quality,
            )

            reasons = (
                self._ranking_reasons(
                    horizontal_distance,
                    depth_difference,
                    time_difference,
                    quality,
                )
            )

            observation_id = (
                str(
                    observation.platform_id
                ).strip()
            )

            candidates.append(
                ObservationCandidate(
                    observation_id=observation_id,
                    platform_id=observation_id,
                    latitude=float(
                        observation.latitude
                    ),
                    longitude=float(
                        observation.longitude
                    ),
                    depth_m=float(
                        observation.depth
                    ),
                    time=observation.time,
                    variable=str(
                        observation.variable
                    ),
                    value=float(
                        observation.value
                    ),
                    quality_flag=quality,
                    horizontal_distance_km=round(
                        horizontal_distance,
                        3,
                    ),
                    depth_difference_m=round(
                        depth_difference,
                        3,
                    ),
                    time_difference_hours=round(
                        time_difference,
                        3,
                    ),
                    comparability_score=round(
                        score,
                        4,
                    ),
                    ranking_reasons=reasons,
                )
            )

        candidates.sort(
            key=lambda item: (
                -item.comparability_score,
                item.horizontal_distance_km,
                item.depth_difference_m,
                item.time_difference_hours,
                item.platform_id,
            )
        )

        candidates = candidates[:limit]

        return NearestObservationResponse(
            requested_latitude=float(
                latitude
            ),
            requested_longitude=float(
                longitude
            ),
            requested_depth_m=float(
                depth_m
            ),
            requested_time=time,
            variable=normalized_variable,
            candidates=candidates,
            count=len(candidates),
        )

    # ----------------------------------------------------------
    # VARIABLE NORMALIZATION
    # ----------------------------------------------------------

    @staticmethod
    def _normalize_variable(
        variable: str,
    ) -> str:
        """Normalize public variable names."""

        normalized = (
            str(variable)
            .strip()
            .lower()
        )

        aliases = {
            "temperature": "thetao",
            "temp": "thetao",
            "salinity": "so",
            "eastward_velocity": "uo",
            "northward_velocity": "vo",
            "u": "uo",
            "v": "vo",
        }

        return aliases.get(
            normalized,
            normalized,
        )

    @classmethod
    def _variable_matches(
        cls,
        observation_variable: str,
        requested_variable: str,
    ) -> bool:
        """Check whether two variable names refer to the same field."""

        normalized_observation = (
            cls._normalize_variable(
                observation_variable
            )
        )

        normalized_requested = (
            cls._normalize_variable(
                requested_variable
            )
        )

        return (
            normalized_observation
            == normalized_requested
        )

    # ----------------------------------------------------------
    # DISTANCE
    # ----------------------------------------------------------

    @staticmethod
    def _haversine_distance(
        latitude_1: float,
        longitude_1: float,
        latitude_2: float,
        longitude_2: float,
    ) -> float:
        """
        Calculate great-circle distance in kilometres.
        """

        from math import (
            asin,
            cos,
            radians,
            sin,
            sqrt,
        )

        earth_radius_km = 6371.0088

        lat1 = radians(
            float(latitude_1)
        )
        lat2 = radians(
            float(latitude_2)
        )

        delta_lat = radians(
            float(latitude_2)
            - float(latitude_1)
        )

        delta_lon = radians(
            float(longitude_2)
            - float(longitude_1)
        )

        a = (
            sin(delta_lat / 2) ** 2
            + cos(lat1)
            * cos(lat2)
            * sin(delta_lon / 2) ** 2
        )

        return (
            2
            * earth_radius_km
            * asin(
                sqrt(a)
            )
        )

    # ----------------------------------------------------------
    # TIME
    # ----------------------------------------------------------

    @staticmethod
    def _time_difference_hours(
        requested_time: datetime,
        observation_time: datetime,
    ) -> float:
        """Return absolute time difference in hours."""

        requested = (
            requested_time
        )

        observed = (
            observation_time
        )

        # Handle naive and timezone-aware timestamps
        # consistently for the current MVP.
        if (
            requested.tzinfo is not None
            and observed.tzinfo is None
        ):
            requested = (
                requested.replace(
                    tzinfo=None
                )
            )

        if (
            requested.tzinfo is None
            and observed.tzinfo is not None
        ):
            observed = (
                observed.replace(
                    tzinfo=None
                )
            )

        return abs(
            (
                requested
                - observed
            ).total_seconds()
        ) / 3600.0

    # ----------------------------------------------------------
    # SCORE
    # ----------------------------------------------------------

    @classmethod
    def _comparability_score(
        cls,
        *,
        horizontal_distance_km: float,
        depth_difference_m: float,
        time_difference_hours: float,
        quality_flag: str,
    ) -> float:
        """
        Calculate a transparent 0-1 comparability score.

        This is a ranking heuristic, not a scientific confidence
        value. Scientific confidence is calculated later by the
        collocation engine.
        """

        spatial_score = max(
            0.0,
            1.0
            - (
                horizontal_distance_km
                / cls.MAX_HORIZONTAL_DISTANCE_KM
            ),
        )

        depth_score = max(
            0.0,
            1.0
            - (
                depth_difference_m
                / cls.MAX_DEPTH_DIFFERENCE_M
            ),
        )

        temporal_score = max(
            0.0,
            1.0
            - (
                time_difference_hours
                / cls.MAX_TIME_DIFFERENCE_HOURS
            ),
        )

        quality_score = (
            1.0
            if quality_flag == "PASS"
            else 0.5
            if quality_flag in {
                "UNKNOWN",
                "UNSET",
            }
            else 0.0
        )

        score = (
            spatial_score * 0.40
            + depth_score * 0.30
            + temporal_score * 0.20
            + quality_score * 0.10
        )

        return max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

    # ----------------------------------------------------------
    # EXPLANATION
    # ----------------------------------------------------------

    @staticmethod
    def _ranking_reasons(
        horizontal_distance_km: float,
        depth_difference_m: float,
        time_difference_hours: float,
        quality_flag: str,
    ) -> list[str]:
        """Generate human-readable ranking reasons."""

        reasons: list[str] = []

        if horizontal_distance_km <= 10:
            reasons.append(
                "very close spatial match"
            )
        elif horizontal_distance_km <= 50:
            reasons.append(
                "close spatial match"
            )

        if depth_difference_m <= 5:
            reasons.append(
                "near-identical depth"
            )
        elif depth_difference_m <= 25:
            reasons.append(
                "close depth match"
            )

        if time_difference_hours <= 6:
            reasons.append(
                "near-identical observation time"
            )
        elif time_difference_hours <= 24:
            reasons.append(
                "same-day observation"
            )

        if quality_flag == "PASS":
            reasons.append(
                "quality control passed"
            )
        elif quality_flag not in {
            "UNKNOWN",
            "UNSET",
        }:
            reasons.append(
                "quality flag requires caution"
            )

        return reasons