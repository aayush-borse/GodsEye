from datetime import datetime

from ocean_backend.ai.narrator import EvidenceNarrator
from ocean_backend.models.schemas import ComparisonEvidence, Coordinate4D


def make_evidence(**overrides):
    data = {
        "variable": "temperature",
        "requested": Coordinate4D(
            latitude=10.0,
            longitude=75.0,
            depth_m=50.0,
            time=datetime(2026, 6, 23, 12, 0),
        ),
        "model_value": 19.82,
        "observed_value": 18.91,
        "difference": 0.91,
        "spatial_distance_km": 1.70,
        "temporal_difference_hours": 0.0,
        "depth_difference_m": 0.0,
        "observation_qc": "PASS",
        "interpolation": "trilinear + linear temporal",
        "confidence": "HIGH",
        "confidence_reasons": [
            "Observation passed quality control.",
            "Small spatial separation.",
            "Small depth separation.",
            "Small temporal separation.",
        ],
    }

    data.update(overrides)
    return ComparisonEvidence(**data)


def test_narrator_reports_verified_comparison_values():
    evidence = make_evidence()

    result = EvidenceNarrator().narrate(evidence)

    assert "Temperature comparison" in result
    assert "Model: 19.82" in result
    assert "Observation: 18.91" in result
    assert "Model–observation difference: +0.91" in result
    assert "Confidence: HIGH" in result


def test_narrator_reports_interpolation_and_separation():
    evidence = make_evidence()

    result = EvidenceNarrator().narrate(evidence)

    assert "Interpolation: trilinear + linear temporal" in result
    assert "Spatial separation: 1.70 km" in result
    assert "Depth separation: 0.00 m" in result
    assert "Temporal separation: 0.00 hours" in result


def test_narrator_reports_qc_and_confidence_reasons():
    evidence = make_evidence()

    result = EvidenceNarrator().narrate(evidence)

    assert "Observation QC: PASS" in result
    assert "Why this confidence level:" in result
    assert "Observation passed quality control." in result


def test_narrator_handles_model_only_evidence():
    evidence = make_evidence(
        observed_value=None,
        difference=None,
        spatial_distance_km=None,
        temporal_difference_hours=None,
        depth_difference_m=None,
        observation_qc="UNKNOWN",
        confidence="UNAVAILABLE",
        confidence_reasons=[
            "No observation was selected for comparison."
        ],
    )

    result = EvidenceNarrator().narrate(evidence)

    assert "Temperature model value" in result
    assert "Model: 19.82" in result
    assert "No observation was selected for comparison." in result
    assert "Confidence: UNAVAILABLE" in result