from __future__ import annotations

from ocean_backend.models.schemas import ComparisonEvidence


class EvidenceNarrator:
    """
    Converts verified scientific evidence into a human-readable explanation.

    This class does not calculate scientific values.
    It only presents values and conclusions already contained in
    ComparisonEvidence.
    """

    def narrate(self, evidence: ComparisonEvidence) -> str:
        if evidence.model_value is None:
            return self._narrate_without_model(evidence)

        if evidence.observed_value is None:
            return self._narrate_model_only(evidence)

        return self._narrate_comparison(evidence)

    def _narrate_comparison(
        self,
        evidence: ComparisonEvidence,
    ) -> str:
        lines = [
            f"{self._variable_name(evidence.variable)} comparison",
            "",
            f"Model: {self._format_value(evidence.model_value)}",
            f"Observation: {self._format_value(evidence.observed_value)}",
            (
                "Model–observation difference: "
                f"{self._format_signed(evidence.difference)}"
            ),
            f"Confidence: {evidence.confidence}",
        ]

        if evidence.interpolation:
            lines.append(
                f"Interpolation: {evidence.interpolation}"
            )

        if evidence.spatial_distance_km is not None:
            lines.append(
                "Spatial separation: "
                f"{evidence.spatial_distance_km:.2f} km"
            )

        if evidence.depth_difference_m is not None:
            lines.append(
                "Depth separation: "
                f"{evidence.depth_difference_m:.2f} m"
            )

        if evidence.temporal_difference_hours is not None:
            lines.append(
                "Temporal separation: "
                f"{evidence.temporal_difference_hours:.2f} hours"
            )

        if evidence.observation_qc:
            lines.append(
                f"Observation QC: {evidence.observation_qc}"
            )

        if evidence.confidence_reasons:
            lines.append("")
            lines.append("Why this confidence level:")
            lines.extend(
                f"- {reason}"
                for reason in evidence.confidence_reasons
            )

        return "\n".join(lines)

    def _narrate_model_only(
        self,
        evidence: ComparisonEvidence,
    ) -> str:
        lines = [
            f"{self._variable_name(evidence.variable)} model value",
            "",
            f"Model: {self._format_value(evidence.model_value)}",
            "No observation was selected for comparison.",
            "Confidence: UNAVAILABLE",
        ]

        if evidence.interpolation:
            lines.append(
                f"Interpolation: {evidence.interpolation}"
            )

        return "\n".join(lines)

    @staticmethod
    def _narrate_without_model(
        evidence: ComparisonEvidence,
    ) -> str:
        return (
            f"{evidence.variable} comparison\n\n"
            "Model value is unavailable."
        )

    @staticmethod
    def _variable_name(variable: str) -> str:
        names = {
            "temperature": "Temperature",
            "salinity": "Salinity",
            "u": "Eastward current",
            "v": "Northward current",
            "chlorophyll": "Chlorophyll",
        }
        return names.get(variable, variable)

    @staticmethod
    def _format_value(value: float | None) -> str:
        if value is None:
            return "N/A"

        return f"{value:.2f}"

    @staticmethod
    def _format_signed(value: float | None) -> str:
        if value is None:
            return "N/A"

        return f"{value:+.2f}"