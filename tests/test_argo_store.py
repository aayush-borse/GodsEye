from pathlib import Path

from ocean_backend.data.argo.store import load_argo_store


ARGO_DATA = Path(
    "src/ocean_backend/data/argo/profiles/1902675_prof.nc"
)


def test_load_real_argo_store():
    store = load_argo_store(str(ARGO_DATA))

    assert store.count() > 0


def test_find_real_argo_observation():
    store = load_argo_store(str(ARGO_DATA))

    observation = store.get_by_id("1902675_1")

    assert observation is not None
    assert observation.platform_id == "1902675_1"
    
    
def test_find_observation_by_profile_variable_and_depth():
    store = load_argo_store(str(ARGO_DATA))

    result = store.get_by_profile(
        profile_id="1902675_1",
        variable="thetao",
        depth=100.0,
    )

    assert result is not None

    observation, depth_difference = result

    assert observation.platform_id == "1902675_1"
    assert observation.variable == "thetao"
    assert observation.depth >= 0
    assert depth_difference >= 0