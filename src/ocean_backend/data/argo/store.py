from ocean_backend.data.argo.adapter import ArgoAdapter
from ocean_backend.data.observation_store import ObservationStore


def load_argo_store(dataset_path: str) -> ObservationStore:
    """Load observations from an Argo GDAC profile file."""

    adapter = ArgoAdapter(dataset_path)

    observations = adapter.load_observations()

    return ObservationStore(observations)