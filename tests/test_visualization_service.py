import numpy as np
import xarray as xr

from ocean_backend.services.upload_service import DatasetRegistry
from ocean_backend.services.visualization_service import VisualizationService


def make_dataset():
    return xr.Dataset(
        {
            "thetao": (("time", "depth", "latitude", "longitude"), np.arange(2 * 3 * 4 * 5, dtype=float).reshape(2, 3, 4, 5)),
            "so": (("time", "depth", "latitude", "longitude"), np.ones((2, 3, 4, 5)) * 35),
            "uo": (("time", "depth", "latitude", "longitude"), np.ones((2, 3, 4, 5)) * 0.2),
            "vo": (("time", "depth", "latitude", "longitude"), np.ones((2, 3, 4, 5)) * 0.1),
        },
        coords={
            "time": np.array(["2024-01-01", "2024-01-02"], dtype="datetime64[ns]"),
            "depth": [0.0, 50.0, 100.0],
            "latitude": [-10.0, -5.0, 0.0, 5.0],
            "longitude": [70.0, 75.0, 80.0, 85.0, 90.0],
        },
    )


def make_service():
    registry = DatasetRegistry()
    registry.register("demo", make_dataset(), None, None)
    return VisualizationService(registry)


def test_manifest_exposes_3d_capabilities():
    manifest = make_service().manifest("demo")
    assert manifest["capabilities"]["volume"] is True
    assert manifest["capabilities"]["horizontal_slice"] is True
    assert manifest["capabilities"]["vectors"] is True


def test_volume_binary_has_renderer_metadata():
    data, meta = make_service().volume_binary("demo", "temperature", stride=2)
    assert len(data) == 2 * 2 * 3 * 4
    assert meta["shape"] == [2, 2, 3]
    assert meta["dtype"] == "float32"


def test_slice_binary_selects_nearest_depth():
    data, meta = make_service().slice_binary("demo", "temperature", depth=49)
    assert meta["selected_depth"] == 50.0
    assert meta["shape"] == [4, 5]
    assert len(data) == 4 * 5 * 4


def test_vectors_are_interleaved_uv():
    data, meta = make_service().vector_binary("demo", depth=50, stride=2)
    assert meta["layout"] == "interleaved_uv"
    assert meta["components"] == 2
    assert meta["shape"] == [2, 3]
    assert len(data) == 2 * 3 * 2 * 4


def test_point_query_returns_nearest_grid_value():
    result = make_service().point_query("demo", -4.9, 74.9, 51, variable="temperature")
    assert result["selected"]["latitude"] == -5.0
    assert result["selected"]["longitude"] == 75.0
    assert result["selected"]["depth"] == 50.0
