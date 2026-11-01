"""High-performance 3D visualization data API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from ocean_backend.services.dataset_runtime import dataset_registry
from ocean_backend.services.upload_service import DatasetNotFoundError
from ocean_backend.services.visualization_service import (
    VisualizationDataError,
    VisualizationService,
)


router = APIRouter(prefix="/visualization", tags=["visualization"])
service = VisualizationService(dataset_registry)


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, DatasetNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _binary_response(data: bytes, metadata: dict, prefix: str) -> Response:
    headers = {
        f"X-{prefix}-Dtype": "float32",
        f"X-{prefix}-Shape": ",".join(str(x) for x in metadata["shape"]),
        f"X-{prefix}-Byte-Order": "little-endian",
        "X-Visualization-Metadata": _compact_metadata(metadata),
    }
    return Response(content=data, media_type="application/octet-stream", headers=headers)


def _compact_metadata(metadata: dict) -> str:
    """Keep binary headers useful without putting large coordinate arrays in them."""
    import json

    compact = {key: value for key, value in metadata.items() if key != "coordinates"}
    return json.dumps(compact, separators=(",", ":"))


@router.get("/{dataset_id}/manifest")
def get_visualization_manifest(dataset_id: str) -> dict:
    """Return the capabilities and coordinate contract used by the 3D renderer."""
    try:
        return service.manifest(dataset_id)
    except (DatasetNotFoundError, VisualizationDataError) as exc:
        raise _error(exc) from exc


@router.get("/{dataset_id}/volume/binary")
def get_visualization_volume(
    dataset_id: str,
    variable: str = Query("temperature"),
    time_index: int = Query(0, ge=0),
    depth_min: float | None = Query(None),
    depth_max: float | None = Query(None),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    stride: int | None = Query(None, ge=1, le=20),
    lod: str | None = Query(None),
) -> Response:
    """Stream a bounded 3D scalar field as little-endian float32."""
    try:
        data, metadata = service.volume_binary(
            dataset_id,
            variable,
            time_index,
            depth_min,
            depth_max,
            latitude_min,
            latitude_max,
            longitude_min,
            longitude_max,
            stride,
            lod,
        )
        return _binary_response(data, metadata, "Volume")
    except (DatasetNotFoundError, VisualizationDataError) as exc:
        raise _error(exc) from exc


@router.get("/{dataset_id}/slice/binary")
def get_visualization_slice(
    dataset_id: str,
    variable: str = Query("temperature"),
    depth: float = Query(...),
    time_index: int = Query(0, ge=0),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    stride: int = Query(1, ge=1, le=20),
) -> Response:
    """Stream a horizontal depth slice for WebGL texture generation."""
    try:
        data, metadata = service.slice_binary(
            dataset_id,
            variable,
            depth,
            time_index,
            latitude_min,
            latitude_max,
            longitude_min,
            longitude_max,
            stride,
        )
        return _binary_response(data, metadata, "Slice")
    except (DatasetNotFoundError, VisualizationDataError) as exc:
        raise _error(exc) from exc


@router.get("/{dataset_id}/vectors/binary")
def get_visualization_vectors(
    dataset_id: str,
    time_index: int = Query(0, ge=0),
    depth: float | None = Query(None),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    stride: int = Query(4, ge=1, le=20),
) -> Response:
    """Stream U/V current vectors as interleaved float32 pairs."""
    try:
        data, metadata = service.vector_binary(
            dataset_id,
            time_index,
            depth,
            latitude_min,
            latitude_max,
            longitude_min,
            longitude_max,
            stride,
        )
        return _binary_response(data, metadata, "Vectors")
    except (DatasetNotFoundError, VisualizationDataError) as exc:
        raise _error(exc) from exc


@router.get("/{dataset_id}/point")
def get_visualization_point(
    dataset_id: str,
    latitude: float = Query(...),
    longitude: float = Query(...),
    depth: float = Query(..., ge=0),
    time_index: int = Query(0, ge=0),
    variable: str = Query("temperature"),
) -> dict:
    """Return the model value nearest to a clicked 3D location."""
    try:
        return service.point_query(
            dataset_id,
            latitude,
            longitude,
            depth,
            time_index,
            variable,
        )
    except (DatasetNotFoundError, VisualizationDataError) as exc:
        raise _error(exc) from exc
