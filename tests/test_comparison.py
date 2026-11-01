import numpy as np
import pytest

from ocean_backend.science.comparison import bias, difference, mae, rmse
from ocean_backend.science.comparison import model_observation_difference


def test_difference_is_model_minus_observation():
    assert difference(19.82, 18.91) == pytest.approx(0.91)


def test_basic_statistics():
    model = np.array([2.0, 4.0])
    obs = np.array([1.0, 3.0])
    assert bias(model, obs) == 1.0
    assert mae(model, obs) == 1.0
    assert rmse(model, obs) == 1.0
    
    
    
def test_model_observation_difference():
    result = model_observation_difference(
        model_value=19.82,
        observation_value=18.91,
    )

    assert result == pytest.approx(0.91)


def test_negative_model_observation_difference():
    result = model_observation_difference(
        model_value=18.20,
        observation_value=19.00,
    )

    assert result == pytest.approx(-0.80)


def test_equal_model_observation_difference():
    result = model_observation_difference(
        model_value=20.0,
        observation_value=20.0,
    )

    assert result == pytest.approx(0.0)
