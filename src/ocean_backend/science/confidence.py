"""Scientific confidence assessment for model-observation comparisons."""


def calculate_confidence(
    quality_flag: str,
    distance_km: float,
    depth_difference_m: float,
    time_difference_hours: float,
) -> tuple[str, list[str]]:
    """
    Calculate an explainable comparison-confidence level.

    The confidence describes how suitable the available evidence
    is for interpreting a model-observation comparison.

    It does NOT describe whether the model is correct.

    Thresholds are deliberately simple and explainable for the MVP.
    """

    quality_flag = quality_flag.strip().upper()

    reasons: list[str] = []

    if quality_flag == "FAIL":
        reasons.append(
            "Observation failed quality control."
        )

        return "LOW", reasons

    if quality_flag == "UNKNOWN":
        reasons.append(
            "Observation quality status is unknown."
        )

    if distance_km > 50.0:
        reasons.append(
            "Observation is far from the nearest model grid point."
        )

    if depth_difference_m > 25.0:
        reasons.append(
            "Observation depth differs substantially "
            "from the requested comparison depth."
        )

    if time_difference_hours > 24.0:
        reasons.append(
            "Observation is far from the nearest model output time."
        )

    if (
        quality_flag != "FAIL"
        and (
            distance_km > 50.0
            or depth_difference_m > 25.0
            or time_difference_hours > 24.0
        )
    ):
        return "LOW", reasons

    if quality_flag == "SUSPECT":
        reasons.append(
            "Observation has a suspect quality flag."
        )

        return "MEDIUM", reasons

    if quality_flag == "UNKNOWN":
        return "MEDIUM", reasons

    if (
        distance_km <= 10.0
        and depth_difference_m <= 10.0
        and time_difference_hours <= 6.0
    ):
        reasons.extend(
            [
                "Observation passed quality control.",
                "Small spatial separation.",
                "Small depth separation.",
                "Small temporal separation.",
            ]
        )

        return "HIGH", reasons

    reasons.extend(
        [
            "Observation passed quality control.",
            "Comparison is spatially supported by the model grid.",
        ]
    )

    if distance_km > 10.0:
        reasons.append(
            "Spatial separation exceeds the high-confidence threshold."
        )

    if depth_difference_m > 10.0:
        reasons.append(
            "Depth separation exceeds the high-confidence threshold."
        )

    if time_difference_hours > 6.0:
        reasons.append(
            "Temporal separation exceeds the high-confidence threshold."
        )

    return "MEDIUM", reasons