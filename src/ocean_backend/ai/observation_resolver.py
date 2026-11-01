from __future__ import annotations

from ocean_backend.data.observation_store import ObservationStore
from ocean_backend.data.observations import Observation


class ObservationResolver:
    """
    Resolves AI observation selectors into concrete observations.

    The resolver performs lookup only. It does not perform scientific
    calculations or interpolation.
    """

    def __init__(
        self,
        observation_store: ObservationStore,
    ) -> None:
        self.observation_store = observation_store

    def resolve(
        self,
        observation_id: str,
    ) -> Observation:
        observation = self.observation_store.get_by_id(
            observation_id
        )

        if observation is None:
            raise ValueError(
                f"Observation '{observation_id}' was not found."
            )

        return observation