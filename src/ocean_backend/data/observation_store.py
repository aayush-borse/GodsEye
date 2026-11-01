"""In-memory observation store used by the scientific backend."""

from __future__ import annotations

from ocean_backend.data.observations import Observation


class ObservationStore:
    """
    In-memory store for ocean observations.

    The current Argo data uses identifiers such as:

        1902675_1
        1902675_2
        1902675_3

    where the prefix identifies the float and the suffix identifies
    the profile/cycle.

    Therefore this store supports both:

        1902675
        1902675_1

    as selectors.
    """

    def __init__(
        self,
        observations: list[Observation] | None = None,
    ) -> None:
        self.observations: list[Observation] = (
            list(observations)
            if observations is not None
            else []
        )

    # ------------------------------------------------------------------
    # BASIC OPERATIONS
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the number of observations stored."""
        return len(self.observations)

    def add(
        self,
        observation: Observation,
    ) -> None:
        """Add an observation to the store."""
        self.observations.append(observation)

    # ------------------------------------------------------------------
    # IDENTIFIER HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _base_platform_id(
        platform_id: str,
    ) -> str:
        """
        Extract the base Argo float ID.

        Examples:

            1902675     -> 1902675
            1902675_1   -> 1902675
            1902675_25  -> 1902675
        """

        value = str(
            platform_id
        ).strip()

        if "_" in value:
            return value.split(
                "_",
                1,
            )[0]

        return value

    # ------------------------------------------------------------------
    # GENERIC OBSERVATION LOOKUP
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        observation_id: str,
    ) -> Observation | None:
        """
        Resolve an observation selector.

        Supported selectors include:

        1. Exact profile/observation ID:
               1902675_25

        2. Base Argo float/platform ID:
               1902675

        For a base platform ID, the first observation belonging to
        that float is returned. ModelService subsequently selects
        the measurement closest to the requested depth.
        """

        selector = str(
            observation_id
        ).strip()

        if not selector:
            return None

        # --------------------------------------------------------------
        # 1. Exact identifier
        # --------------------------------------------------------------

        for observation in self.observations:
            current_id = str(
                observation.platform_id
            ).strip()

            if current_id == selector:
                return observation

        # --------------------------------------------------------------
        # 2. Base platform/float identifier
        # --------------------------------------------------------------

        selector_base = (
            self._base_platform_id(
                selector
            )
        )

        for observation in self.observations:
            current_id = str(
                observation.platform_id
            ).strip()

            current_base = (
                self._base_platform_id(
                    current_id
                )
            )

            if current_base == selector_base:
                return observation

        # --------------------------------------------------------------
        # 3. Future explicit observation_id support
        # --------------------------------------------------------------

        for observation in self.observations:
            generated_id = getattr(
                observation,
                "observation_id",
                None,
            )

            if generated_id is None:
                continue

            if (
                str(generated_id).strip()
                == selector
            ):
                return observation

        return None

    # ------------------------------------------------------------------
    # PLATFORM LOOKUP
    # ------------------------------------------------------------------

    def get_by_platform(
        self,
        platform_id: str,
    ) -> Observation | None:
        """
        Return the first observation belonging to a platform/float.

        Both of these are accepted:

            1902675
            1902675_1
        """

        selector = str(
            platform_id
        ).strip()

        if not selector:
            return None

        selector_base = (
            self._base_platform_id(
                selector
            )
        )

        for observation in self.observations:
            current_base = (
                self._base_platform_id(
                    observation.platform_id
                )
            )

            if current_base == selector_base:
                return observation

        return None

    # ------------------------------------------------------------------
    # PROFILE / DEPTH LOOKUP
    # ------------------------------------------------------------------

    def get_by_profile(
        self,
        profile_id: str,
        variable: str,
        depth: float,
    ) -> tuple[Observation, float] | None:
        """
        Return the observation nearest to the requested depth.

        ``profile_id`` may be:

            1902675
            1902675_1
            1902675_25

        If a base float ID is supplied, all observations belonging to
        that float are considered.

        If an exact profile ID is supplied, only that profile is
        considered.

        The returned depth difference is:

            abs(observation_depth - requested_depth)
        """

        selector = str(
            profile_id
        ).strip()

        requested_variable = str(
            variable
        ).strip()

        requested_depth = float(
            depth
        )

        if not selector:
            return None

        selector_base = (
            self._base_platform_id(
                selector
            )
        )

        # Determine whether the caller supplied an exact profile ID.
        exact_profile_requested = (
            "_" in selector
        )

        candidates: list[Observation] = []

        for observation in self.observations:
            current_id = str(
                observation.platform_id
            ).strip()

            current_base = (
                self._base_platform_id(
                    current_id
                )
            )

            # Variable must match.
            if (
                str(
                    observation.variable
                ).strip()
                != requested_variable
            ):
                continue

            # Exact profile lookup.
            if exact_profile_requested:
                if current_id != selector:
                    continue

            # Base platform lookup.
            else:
                if current_base != selector_base:
                    continue

            candidates.append(
                observation
            )

        if not candidates:
            return None

        # Select the physical measurement closest to the requested
        # depth.
        observation = min(
            candidates,
            key=lambda item: abs(
                float(item.depth)
                - requested_depth
            ),
        )

        depth_difference = abs(
            float(observation.depth)
            - requested_depth
        )

        return (
            observation,
            float(depth_difference),
        )