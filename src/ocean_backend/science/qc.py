VALID_QC_FLAGS = {
    "PASS",
    "SUSPECT",
    "FAIL",
}


def validate_quality_flag(quality_flag: str) -> str:
    """
    Validate and normalize an observation quality flag.
    """

    normalized = quality_flag.strip().upper()

    if normalized not in VALID_QC_FLAGS:
        raise ValueError(
            f"Unknown quality flag: {quality_flag}"
        )

    return normalized