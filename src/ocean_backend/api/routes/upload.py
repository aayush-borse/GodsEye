"""Dataset upload, metadata, and data access routes."""

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
)

from ocean_backend.models.datasets import (
    DatasetCoordinateMetadataResponse,
    DatasetDataResponse,
    DatasetMetadata,
    DatasetSliceResponse,
    DatasetUploadResponse,
    DatasetVolumeResponse,
)
from ocean_backend.services.dataset_runtime import dataset_registry
from ocean_backend.services.dataset_service import (
    DatasetDataError,
    DatasetDataService,
)
from ocean_backend.services.upload_service import (
    DatasetNotFoundError,
    DatasetUploadError,
    DatasetUploadService,
)


router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
)


# --------------------------------------------------------------
# Services use the shared dataset registry.
# --------------------------------------------------------------

upload_service = DatasetUploadService(
    registry=dataset_registry,
)

data_service = DatasetDataService(
    dataset_registry,
)


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
)
async def upload_dataset(
    file: UploadFile = File(...),
) -> DatasetUploadResponse:
    """Upload a NetCDF dataset."""

    try:
        return upload_service.upload(
            file=file.file,
            filename=file.filename or "",
            content_type=file.content_type,
        )

    except DatasetUploadError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}",
    response_model=DatasetMetadata,
)
def get_dataset_metadata(
    dataset_id: str,
) -> DatasetMetadata:
    """Return metadata for an uploaded dataset."""

    try:
        return dataset_registry.get_metadata(
            dataset_id,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}/coordinates",
    response_model=DatasetCoordinateMetadataResponse,
)
def get_dataset_coordinates(
    dataset_id: str,
) -> DatasetCoordinateMetadataResponse:
    """
    Return geographic, depth, and time coordinates for a dataset.

    This endpoint gives the visualization frontend the real coordinate
    system of the dataset so array indices can be mapped to physical
    latitude, longitude, depth, and time values.
    """

    try:
        return data_service.get_coordinate_metadata(
            dataset_id=dataset_id,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetDataError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}/data",
    response_model=DatasetDataResponse,
)
def get_dataset_data(
    dataset_id: str,
    variable: str = Query(...),
    time_index: int = Query(0, ge=0),
    depth_min: float | None = Query(None),
    depth_max: float | None = Query(None),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    depth_stride: int = Query(1, ge=1),
    latitude_stride: int = Query(1, ge=1),
    longitude_stride: int = Query(1, ge=1),
) -> DatasetDataResponse:
    """Return a selected portion of a dataset variable."""

    try:
        return data_service.get_data(
            dataset_id=dataset_id,
            variable=variable,
            time_index=time_index,
            depth_min=depth_min,
            depth_max=depth_max,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
            depth_stride=depth_stride,
            latitude_stride=latitude_stride,
            longitude_stride=longitude_stride,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetDataError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}/slice",
    response_model=DatasetSliceResponse,
)
def get_dataset_slice(
    dataset_id: str,
    variable: str = Query(...),
    depth: float = Query(...),
    time_index: int = Query(0, ge=0),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    latitude_stride: int = Query(1, ge=1),
    longitude_stride: int = Query(1, ge=1),
) -> DatasetSliceResponse:
    """Return the horizontal slice nearest to a requested depth."""

    try:
        return data_service.get_slice(
            dataset_id=dataset_id,
            variable=variable,
            depth=depth,
            time_index=time_index,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
            latitude_stride=latitude_stride,
            longitude_stride=longitude_stride,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetDataError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}/slice/binary",
)
def get_dataset_slice_binary(
    dataset_id: str,
    variable: str = Query(...),
    depth: float = Query(...),
    time_index: int = Query(0, ge=0),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    latitude_stride: int = Query(1, ge=1),
    longitude_stride: int = Query(1, ge=1),
) -> Response:
    """
    Return a horizontal depth slice as raw float32 bytes.

    Intended for high-performance 3D visualization.
    """

    try:
        (
            binary_data,
            shape,
            selected_depth,
        ) = data_service.get_slice_binary(
            dataset_id=dataset_id,
            variable=variable,
            depth=depth,
            time_index=time_index,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
            latitude_stride=latitude_stride,
            longitude_stride=longitude_stride,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetDataError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ----------------------------------------------------------
    # Metadata is placed in headers so the body can remain pure
    # binary numerical data.
    # ----------------------------------------------------------

    shape_header = ",".join(
        str(size)
        for size in shape
    )

    return Response(
        content=binary_data,
        media_type="application/octet-stream",
        headers={
            "X-Slice-Dtype": "float32",
            "X-Slice-Shape": shape_header,
            "X-Slice-Depth": str(selected_depth),
            "X-Slice-Byte-Order": "little-endian",
        },
    )


@router.get(
    "/{dataset_id}/volume",
    response_model=DatasetVolumeResponse,
)
def get_dataset_volume(
    dataset_id: str,
    variable: str = Query(...),
    time_index: int = Query(0, ge=0),
    depth_min: float | None = Query(None),
    depth_max: float | None = Query(None),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    depth_stride: int = Query(1, ge=1),
    latitude_stride: int = Query(1, ge=1),
    longitude_stride: int = Query(1, ge=1),
) -> DatasetVolumeResponse:
    """Return a three-dimensional variable volume as JSON."""

    try:
        return data_service.get_volume(
            dataset_id=dataset_id,
            variable=variable,
            time_index=time_index,
            depth_min=depth_min,
            depth_max=depth_max,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
            depth_stride=depth_stride,
            latitude_stride=latitude_stride,
            longitude_stride=longitude_stride,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetDataError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}/volume/binary",
)
def get_dataset_volume_binary(
    dataset_id: str,
    variable: str = Query(...),
    time_index: int = Query(0, ge=0),
    depth_min: float | None = Query(None),
    depth_max: float | None = Query(None),
    latitude_min: float | None = Query(None),
    latitude_max: float | None = Query(None),
    longitude_min: float | None = Query(None),
    longitude_max: float | None = Query(None),
    depth_stride: int = Query(1, ge=1),
    latitude_stride: int = Query(1, ge=1),
    longitude_stride: int = Query(1, ge=1),
) -> Response:
    """
    Return a three-dimensional variable as raw float32 bytes.

    Intended for the high-performance 3D visualization frontend.
    """

    try:
        binary_data, shape = data_service.get_volume_binary(
            dataset_id=dataset_id,
            variable=variable,
            time_index=time_index,
            depth_min=depth_min,
            depth_max=depth_max,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
            depth_stride=depth_stride,
            latitude_stride=latitude_stride,
            longitude_stride=longitude_stride,
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetDataError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    shape_header = ",".join(
        str(size)
        for size in shape
    )

    return Response(
        content=binary_data,
        media_type="application/octet-stream",
        headers={
            "X-Volume-Dtype": "float32",
            "X-Volume-Shape": shape_header,
            "X-Volume-Byte-Order": "little-endian",
        },
    )