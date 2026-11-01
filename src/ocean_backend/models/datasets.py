"""Models used by the dataset API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetVariable(BaseModel):
    """Metadata for one data variable."""

    name: str
    dimensions: list[str]
    shape: list[int]
    dtype: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class DatasetCoordinate(BaseModel):
    """Metadata for one coordinate."""

    name: str
    dimensions: list[str]
    shape: list[int]
    dtype: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    min_value: Any | None = None
    max_value: Any | None = None


class DatasetMetadata(BaseModel):
    """Metadata returned for an uploaded dataset."""

    dataset_id: str
    filename: str
    format: str = "NetCDF"
    dimensions: dict[str, int]
    coordinates: list[DatasetCoordinate]
    variables: list[DatasetVariable]
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DatasetUploadResponse(BaseModel):
    """Response returned after a dataset is uploaded."""

    dataset_id: str
    filename: str
    metadata: DatasetMetadata


class DatasetDataResponse(BaseModel):
    """Generic response containing a selected dataset variable."""

    dataset_id: str
    variable: str
    dimensions: list[str]
    shape: list[int]
    coordinates: dict[str, list[Any]]
    values: list[Any]


class DatasetSliceResponse(BaseModel):
    """Response containing a two-dimensional depth slice."""

    dataset_id: str
    variable: str
    depth: float
    dimensions: list[str]
    shape: list[int]
    coordinates: dict[str, list[Any]]
    values: list[Any]


class DatasetVolumeResponse(BaseModel):
    """Response containing a three-dimensional volume."""

    dataset_id: str
    variable: str
    dimensions: list[str]
    shape: list[int]
    coordinates: dict[str, list[Any]]
    values: list[Any]


class CoordinateAxis(BaseModel):
    """Geographic or vertical coordinate information for the renderer."""

    name: str
    min_value: float
    max_value: float
    count: int
    values: list[float]


class DatasetCoordinateMetadataResponse(BaseModel):
    """Coordinate information needed to position a dataset in 3D space."""

    dataset_id: str
    latitude: CoordinateAxis | None = None
    longitude: CoordinateAxis | None = None
    depth: CoordinateAxis | None = None
    time: list[Any] = Field(default_factory=list)