import numpy as np
import pytest
import xarray as xr


from ocean_backend.science.interpolation import linear_time, trilinear,  interpolate_4d


def test_linear_time_midpoint():
    assert linear_time(10.0, 20.0, 0.5) == 15.0


def test_trilinear_constant_field():
    corners = np.full((2, 2, 2), 7.5)
    assert trilinear(corners, 0.2, 0.7, 0.4) == pytest.approx(7.5)


def test_trilinear_rejects_wrong_shape():
    try:
        trilinear(np.zeros((2, 2)), 0.5, 0.5, 0.5)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
def test_interpolate_3d_constant_field():
    import numpy as np
    import xarray as xr

    from ocean_backend.science.interpolation import interpolate_3d

    field = xr.DataArray(
        np.full((2, 2, 2), 10.0),
        dims=("depth", "latitude", "longitude"),
        coords={
            "depth": [0.0, 100.0],
            "latitude": [10.0, 20.0],
            "longitude": [60.0, 70.0],
        },
    )

    result = interpolate_3d(
        field,
        latitude=15.0,
        longitude=65.0,
        depth=50.0,
    )

    assert result == pytest.approx(10.0)
    
def test_linear_time():
    result = linear_time(
        v0=18.0,
        v1=20.0,
        alpha=0.5,
    )

    assert result == pytest.approx(19.0)
    
    
def test_linear_time_at_start():
    result = linear_time(
        v0=18.0,
        v1=20.0,
        alpha=0.0,
    )

    assert result == pytest.approx(18.0)


def test_linear_time_at_end():
    result = linear_time(
        v0=18.0,
        v1=20.0,
        alpha=1.0,
    )

    assert result == pytest.approx(20.0)


def test_linear_time_rejects_invalid_alpha():
    with pytest.raises(ValueError):
        linear_time(
            v0=18.0,
            v1=20.0,
            alpha=1.5,
        )

    with pytest.raises(ValueError):
        linear_time(
            v0=18.0,
            v1=20.0,
            alpha=-0.1,
        )
        
        
def test_linear_time_at_start():
    result = linear_time(
        v0=18.0,
        v1=20.0,
        alpha=0.0,
    )

    assert result == pytest.approx(18.0)


def test_linear_time_at_end():
    result = linear_time(
        v0=18.0,
        v1=20.0,
        alpha=1.0,
    )

    assert result == pytest.approx(20.0)


def test_linear_time_rejects_invalid_alpha():
    with pytest.raises(ValueError):
        linear_time(
            v0=18.0,
            v1=20.0,
            alpha=1.5,
        )

    with pytest.raises(ValueError):
        linear_time(
            v0=18.0,
            v1=20.0,
            alpha=-0.1,
        )
        
        
def test_linear_time_with_real_model_values():
    june_22 = 19.121503905573316
    june_23 = 18.962031441050737

    result = linear_time(
        v0=june_22,
        v1=june_23,
        alpha=0.5,
    )

    assert result == pytest.approx(19.041767673312027)
    
def test_interpolate_4d_with_real_model_data():
    ds = xr.open_dataset(
        "src/ocean_backend/data/model_4d.nc"
    )

    result = interpolate_4d(
        ds["thetao"],
        latitude=12.5,
        longitude=70.5,
        depth=150.0,
        time=np.datetime64(
            "2026-06-22T12:00:00"
        ),
    )

    ds.close()

    assert result == pytest.approx(
        24.941710472106937
    )