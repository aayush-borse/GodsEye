"""Build standardized evidence packets from scientific comparisons."""

from __future__ import annotations

from ocean_backend.models.schemas import (
    ComparisonEvidence,
)
from ocean_backend.models.evidence import (
    EvidenceCollocation,
    EvidenceConfidence,
    EvidenceDifference,
    EvidenceModel,
    EvidenceObservation,
    EvidencePacket,
    EvidenceProvenance,
)


class EvidenceService:
    """Convert scientific comparison results into evidence packets."""

    def build_packet(
        self,
        comparison: ComparisonEvidence,
        dataset_id: str,
        observation_id: str,
        observation_source: str = "ARGO",
    ) -> EvidencePacket:
        """Build a traceable evidence packet."""

        if comparison.observed_value is None:
            raise ValueError(
                "An evidence packet requires an observation."
            )

        if comparison.difference is None:
            raise ValueError(
                "An evidence packet requires a model-observation difference."
            )

        if comparison.spatial_distance_km is None:
            raise ValueError(
                "An evidence packet requires spatial collocation metadata."
            )

        if comparison.depth_difference_m is None:
            raise ValueError(
                "An evidence packet requires depth collocation metadata."
            )

        if comparison.temporal_difference_hours is None:
            raise ValueError(
                "An evidence packet requires temporal collocation metadata."
            )

        return EvidencePacket(
            observation_id=observation_id,
            variable=comparison.variable,

            model=EvidenceModel(
                value=float(
                    comparison.model_value
                ),
                dataset_id=dataset_id,
                interpolation=(
                    comparison.interpolation
                ),
            ),

            observation=EvidenceObservation(
                value=float(
                    comparison.observed_value
                ),
                observation_id=observation_id,
                source=observation_source,
                quality_control=(
                    comparison.observation_qc
                ),
            ),

            difference=EvidenceDifference(
                value=float(
                    comparison.difference
                ),
                absolute=abs(
                    float(
                        comparison.difference
                    )
                ),
            ),

            collocation=EvidenceCollocation(
                horizontal_distance_km=float(
                    comparison.spatial_distance_km
                ),
                depth_difference_m=float(
                    comparison.depth_difference_m
                ),
                time_difference_hours=float(
                    comparison.temporal_difference_hours
                ),
            ),

            confidence=EvidenceConfidence(
                level=comparison.confidence,
                reasons=list(
                    comparison.confidence_reasons
                ),
            ),

            provenance=EvidenceProvenance(
                model_dataset=dataset_id,
                observation_source=observation_source,
                interpolation_method=(
                    comparison.interpolation
                ),
            ),
        )