"""Natural-language intent parser for the ocean intelligence layer."""

from __future__ import annotations

import re

from ocean_backend.ai.commands import CommandType, OceanCommand


class OceanCommandParser:
    """
    Convert simple natural-language requests into structured commands.

    This parser is intentionally deterministic for the MVP.

    A future LLM can replace or sit in front of this parser, but it
    must still produce the same OceanCommand contract.
    """

    def parse(
        self,
        text: str,
        dataset_id: str | None = None,
        observation_id: str | None = None,
    ) -> OceanCommand:
        """Parse a user request into an OceanCommand."""

        text = text.strip()

        if not text:
            raise ValueError(
                "Command text cannot be empty."
            )

        lowered = text.lower()

        # ------------------------------------------------------
        # Thermocline
        # ------------------------------------------------------

        if "thermocline" in lowered:

            return OceanCommand(
                command=CommandType.SHOW_THERMOCLINE,
                dataset_id=dataset_id,
                variable="temperature",
            )

        # ------------------------------------------------------
        # Model / observation comparison
        # ------------------------------------------------------

        if (
            "compare" in lowered
            and (
                "model" in lowered
                or "observation" in lowered
                or "argo" in lowered
            )
        ):

            resolved_observation_id = (
                self._extract_observation_id(
                    text
                )
                or observation_id
            )

            variable = (
                self._extract_variable(
                    lowered
                )
            )

            return OceanCommand(
                command=(
                    CommandType
                    .COMPARE_MODEL_OBSERVATION
                ),
                dataset_id=dataset_id,
                observation_id=resolved_observation_id,
                variable=variable or "temperature",
            )

        # ------------------------------------------------------
        # Natural-language comparison phrasing
        # ------------------------------------------------------

        if (
            "why is this float" in lowered
            or "why is this observation" in lowered
            or "model vs obs" in lowered
            or "model versus obs" in lowered
        ):
            return OceanCommand(
                command=CommandType.COMPARE_MODEL_OBSERVATION,
                dataset_id=dataset_id,
                observation_id=(
                    self._extract_observation_id(text)
                    or observation_id
                ),
                variable=self._extract_variable(lowered) or "temperature",
            )

        # ------------------------------------------------------
        # Difference
        # ------------------------------------------------------

        if (
            "difference" in lowered
            or "disagreement" in lowered
            or "model minus observation" in lowered
        ):

            return OceanCommand(
                command=CommandType.SHOW_DIFFERENCE,
                dataset_id=dataset_id,
                variable=self._extract_variable(
                    lowered
                ),
            )

        # ------------------------------------------------------
        # Profile
        # ------------------------------------------------------

        if "profile" in lowered:

            observation_id = (
                self._extract_observation_id(
                    text
                )
            )

            return OceanCommand(
                command=CommandType.SHOW_PROFILE,
                observation_id=observation_id,
                variable=self._extract_variable(lowered),
            )

        # ------------------------------------------------------
        # Show observations
        # ------------------------------------------------------

        if (
            "observation" in lowered
            or "argo" in lowered
            or "glider" in lowered
        ):
            return OceanCommand(
                command=CommandType.SHOW_OBSERVATIONS,
                dataset_id=dataset_id,
            )

        # ------------------------------------------------------
        # Depth filter
        # ------------------------------------------------------

        if "depth" in lowered:

            depth = (
                self._extract_depth(
                    text
                )
            )

            if depth is not None:

                return OceanCommand(
                    command=CommandType.FILTER_BY_DEPTH,
                    dataset_id=dataset_id,
                    depth=depth,
                )

        # ------------------------------------------------------
        # Volume
        # ------------------------------------------------------

        variable = self._extract_variable(lowered)

        if (
            "show" in lowered
            or "display" in lowered
            or "visualize" in lowered
            or "view" in lowered
        ):

            return OceanCommand(
                command=CommandType.SHOW_VOLUME,
                dataset_id=dataset_id,
                variable=variable,
            )

        # ------------------------------------------------------
        # Variable filter
        # ------------------------------------------------------

        if (
            "temperature" in lowered
            or "salinity" in lowered
            or "current" in lowered
        ):

            return OceanCommand(
                command=CommandType.FILTER_BY_VARIABLE,
                dataset_id=dataset_id,
                variable=variable,
            )

        raise ValueError(
            "Could not determine an ocean visualization command."
        )

    # ----------------------------------------------------------
    # Extraction helpers
    # ----------------------------------------------------------

    @staticmethod
    def _extract_variable(
        text: str,
    ) -> str | None:
        """Extract a supported scientific variable."""

        if (
            "temperature" in text
            or "temp" in text
            or "thetao" in text
        ):
            return "temperature"

        if (
            "salinity" in text
            or "salt" in text
            or "so" in text
        ):
            return "salinity"

        if (
            "u current" in text
            or "eastward" in text
            or "uo" in text
        ):
            return "u"

        if (
            "v current" in text
            or "northward" in text
            or "vo" in text
        ):
            return "v"

        if "current" in text:
            return "u"

        return None

    @staticmethod
    def _extract_depth(
        text: str,
    ) -> float | None:
        """Extract a depth expressed in metres."""

        patterns = [
            r"depth\s*(?:of|at|=)?\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*(?:m|meters|metres)\s*(?:depth)?",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:

                return float(
                    match.group(1)
                )

        return None

    @staticmethod
    def _extract_observation_id(
        text: str,
    ) -> str | None:
        """
        Extract an observation identifier.

        Supports identifiers such as:
        1902675
        ARGO-1902675
        observation 1902675
        """

        match = re.search(
            r"(?:argo[-_\s]*)?(\d{5,})",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return None