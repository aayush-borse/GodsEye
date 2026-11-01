import pytest

from ocean_backend.science.qc import validate_quality_flag


def test_valid_pass_flag():
    result = validate_quality_flag("PASS")

    assert result == "PASS"


def test_valid_suspect_flag():
    result = validate_quality_flag("SUSPECT")

    assert result == "SUSPECT"


def test_valid_fail_flag():
    result = validate_quality_flag("FAIL")

    assert result == "FAIL"


def test_lowercase_flag_is_normalized():
    result = validate_quality_flag("pass")

    assert result == "PASS"


def test_invalid_flag():
    with pytest.raises(ValueError):
        validate_quality_flag("UNKNOWN")