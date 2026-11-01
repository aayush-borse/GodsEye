from datetime import datetime

from ocean_backend.ai.narrator import EvidenceNarrator
from ocean_backend.models.schemas import ComparisonEvidence, Coordinate4D


def test_narrator_formats_verified_evidence():
    evidence = ComparisonEvidence(
        variable="temperature",
        requested=Coordinate4D(latitude=10, longitude=75, depth_m=50, time=datetime(2026, 1, 1)),
        model_value=20.0,
        observed_value=19.5,
        difference=0.5,
        interpolation="trilinear",
        confidence="HIGH",
        confidence_reasons=["Small spatial separation."],
    )
    narrative = EvidenceNarrator().narrate(evidence)
    assert "Model: 20.00" in narrative
    assert "Observation: 19.50" in narrative
    assert "Confidence: HIGH" in narrative
