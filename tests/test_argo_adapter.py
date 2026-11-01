from pathlib import Path

from ocean_backend.data.argo.adapter import (
    ArgoAdapter,
    argo_qc_to_internal,
)


MODEL_DATA = Path(
    "src/ocean_backend/data/argo/profiles/1902675_prof.nc"
)


def test_argo_qc_mapping():
    assert argo_qc_to_internal(b"1") == "PASS"
    assert argo_qc_to_internal(b"2") == "PASS"
    assert argo_qc_to_internal(b"3") == "SUSPECT"
    assert argo_qc_to_internal(b"4") == "FAIL"
    assert argo_qc_to_internal(b"9") == "UNKNOWN"


def test_load_real_argo_profiles():
    adapter = ArgoAdapter(str(MODEL_DATA))

    profiles = adapter.load_profiles()

    assert len(profiles) == 2  # Small synthetic demo fixture

    first = profiles[0]

    assert first.platform_id != ""
    assert first.cycle_number >= 0
    assert -90 <= first.latitude <= 90
    assert -180 <= first.longitude <= 180
    assert first.time is not None


def test_real_argo_profile_contains_measurements():
    adapter = ArgoAdapter(str(MODEL_DATA))

    profiles = adapter.load_profiles()

    profile = profiles[0]

    assert len(profile.temperature) > 0
    assert len(profile.salinity) > 0

    temperature = profile.temperature[0]

    assert temperature.pressure >= 0
    assert temperature.quality_flag in {
        "PASS",
        "SUSPECT",
        "FAIL",
        "UNKNOWN",
    }

    assert temperature.value_source in {
        "RAW",
        "ADJUSTED",
    }


def test_load_observations():
    adapter = ArgoAdapter(str(MODEL_DATA))

    observations = adapter.load_observations()

    assert len(observations) > 0

    variables = {observation.variable for observation in observations}

    assert "thetao" in variables
    assert "so" in variables