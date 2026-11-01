"""Dataset upload, validation, and session management."""

from __future__ import annotations

import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

import numpy as np
import xarray as xr

from ocean_backend.models.datasets import (
    DatasetCoordinate,
    DatasetMetadata,
    DatasetUploadResponse,
    DatasetVariable,
)


class DatasetNotFoundError(Exception):
    """Raised when a dataset ID does not exist."""


class DatasetUploadError(Exception):
    """Raised when an uploaded dataset cannot be accepted."""


class DatasetRegistry:
    """Stores uploaded datasets for the lifetime of the backend process."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        if storage_dir is None:
            storage_dir = Path("data") / "uploads"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._datasets: dict[str, xr.Dataset] = {}
        self._metadata: dict[str, DatasetMetadata] = {}
        self._paths: dict[str, Path] = {}

    def register(
        self,
        dataset_id: str,
        dataset: xr.Dataset,
        metadata: DatasetMetadata,
        path: Path,
    ) -> None:
        """Register an opened dataset and its metadata."""

        self._datasets[dataset_id] = dataset
        self._metadata[dataset_id] = metadata
        self._paths[dataset_id] = path

    def get(self, dataset_id: str) -> xr.Dataset:
        """Return an opened dataset by ID."""

        try:
            return self._datasets[dataset_id]
        except KeyError as exc:
            raise DatasetNotFoundError(
                f"Dataset '{dataset_id}' was not found."
            ) from exc

    def get_metadata(self, dataset_id: str) -> DatasetMetadata:
        """Return dataset metadata by ID."""

        try:
            return self._metadata[dataset_id]
        except KeyError as exc:
            raise DatasetNotFoundError(
                f"Dataset '{dataset_id}' was not found."
            ) from exc

    def get_path(self, dataset_id: str) -> Path:
        """Return the stored file path for a dataset."""

        try:
            return self._paths[dataset_id]
        except KeyError as exc:
            raise DatasetNotFoundError(
                f"Dataset '{dataset_id}' was not found."
            ) from exc

    def close(self, dataset_id: str) -> None:
        """Close and remove a registered dataset."""

        dataset = self._datasets.pop(dataset_id, None)

        if dataset is not None:
            dataset.close()

        self._metadata.pop(dataset_id, None)
        self._paths.pop(dataset_id, None)

    def close_all(self) -> None:
        """Close all registered datasets."""

        for dataset_id in list(self._datasets):
            self.close(dataset_id)


class DatasetUploadService:
    """Accepts NetCDF files and creates dataset sessions."""

    MAX_UPLOAD_BYTES = 1_000_000_000

    def __init__(
        self,
        registry: DatasetRegistry | None = None,
    ) -> None:
        # A shared registry must be supplied by the application.
        #
        # This prevents upload routes and data-processing routes
        # from accidentally creating separate in-memory registries.
        if registry is None:
            raise ValueError(
                "DatasetUploadService requires a shared DatasetRegistry."
            )

        self.registry = registry

    def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str | None = None,
    ) -> DatasetUploadResponse:
        """Save, open, validate, and register an uploaded NetCDF file."""

        safe_filename = self._validate_filename(filename)

        dataset_id = uuid.uuid4().hex

        destination = (
            self.registry.storage_dir
            / f"{dataset_id}_{safe_filename}"
        )

        try:
            self._save_upload(file, destination)

            dataset = self._open_dataset(destination)

            metadata = self._build_metadata(
                dataset_id=dataset_id,
                filename=safe_filename,
                dataset=dataset,
            )

            self.registry.register(
                dataset_id=dataset_id,
                dataset=dataset,
                metadata=metadata,
                path=destination,
            )

            return DatasetUploadResponse(
                dataset_id=dataset_id,
                filename=safe_filename,
                metadata=metadata,
            )

        except DatasetUploadError:
            destination.unlink(missing_ok=True)
            raise

        except Exception as exc:
            destination.unlink(missing_ok=True)

            raise DatasetUploadError(
                f"Unable to open the uploaded NetCDF dataset: {exc}"
            ) from exc

    @staticmethod
    def _validate_filename(
        filename: str,
    ) -> str:
        """Validate and sanitize the uploaded filename."""

        name = Path(filename or "").name.strip()

        if not name:
            raise DatasetUploadError(
                "A filename is required."
            )

        if not name.lower().endswith(
            (".nc", ".nc4", ".cdf")
        ):
            raise DatasetUploadError(
                "Only NetCDF files are supported "
                "(.nc, .nc4, .cdf)."
            )

        name = re.sub(
            r"[^A-Za-z0-9._-]",
            "_",
            name,
        )

        return name

    @staticmethod
    def _save_upload(
        file: BinaryIO,
        destination: Path,
    ) -> None:
        """Save the uploaded file while enforcing the size limit."""

        total_bytes = 0
        chunk_size = 1024 * 1024

        with destination.open("wb") as output:
            while True:
                chunk = file.read(chunk_size)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > DatasetUploadService.MAX_UPLOAD_BYTES:
                    raise DatasetUploadError(
                        "Uploaded file is larger than "
                        "the 1 GB upload limit."
                    )

                output.write(chunk)

        if total_bytes == 0:
            raise DatasetUploadError(
                "Uploaded file is empty."
            )

    @staticmethod
    def _open_dataset(
        path: Path,
    ) -> xr.Dataset:
        """Open a NetCDF dataset using xarray."""

        try:
            return xr.open_dataset(
                path,
                decode_cf=True,
            )

        except Exception as exc:
            raise DatasetUploadError(
                "The file is not a readable NetCDF dataset: "
                f"{exc}"
            ) from exc

    @staticmethod
    def _build_metadata(
        dataset_id: str,
        filename: str,
        dataset: xr.Dataset,
    ) -> DatasetMetadata:
        """Build API-safe metadata for the uploaded dataset."""

        coordinates: list[DatasetCoordinate] = []

        for name in dataset.coords:
            coordinate = dataset.coords[name]

            coordinates.append(
                DatasetCoordinate(
                    name=name,
                    dimensions=list(coordinate.dims),
                    shape=[
                        int(value)
                        for value in coordinate.shape
                    ],
                    dtype=str(coordinate.dtype),
                    attributes=DatasetUploadService._json_safe_mapping(
                        coordinate.attrs
                    ),
                    min_value=DatasetUploadService._safe_min(
                        coordinate.values
                    ),
                    max_value=DatasetUploadService._safe_max(
                        coordinate.values
                    ),
                )
            )

        variables: list[DatasetVariable] = []

        for name in dataset.data_vars:
            variable = dataset.data_vars[name]

            variables.append(
                DatasetVariable(
                    name=name,
                    dimensions=list(variable.dims),
                    shape=[
                        int(value)
                        for value in variable.shape
                    ],
                    dtype=str(variable.dtype),
                    attributes=DatasetUploadService._json_safe_mapping(
                        variable.attrs
                    ),
                )
            )

        return DatasetMetadata(
            dataset_id=dataset_id,
            filename=filename,
            dimensions={
                name: int(size)
                for name, size in dataset.sizes.items()
            },
            coordinates=coordinates,
            variables=variables,
            attributes=DatasetUploadService._json_safe_mapping(
                dataset.attrs
            ),
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _json_safe_mapping(
        values: dict,
    ) -> dict:
        """Convert metadata values into JSON-safe values."""

        result: dict = {}

        for key, value in values.items():
            result[str(key)] = (
                DatasetUploadService._json_safe_value(
                    value
                )
            )

        return result

    @staticmethod
    def _json_safe_value(value):
        """Convert a value into something that can be serialized to JSON."""

        if isinstance(value, np.ndarray):
            return [
                DatasetUploadService._json_safe_value(
                    item
                )
                for item in value.tolist()
            ]

        if isinstance(value, np.generic):
            return DatasetUploadService._json_safe_value(
                value.item()
            )

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, float):
            if not math.isfinite(value):
                return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if value is None:
            return None

        return str(value)

    @staticmethod
    def _safe_min(values):
        """Return a JSON-safe minimum value."""

        try:
            array = np.asarray(values)

            if array.size == 0:
                return None

            if np.issubdtype(
                array.dtype,
                np.datetime64,
            ):
                return str(array.min())

            if np.issubdtype(
                array.dtype,
                np.number,
            ):
                finite = array[np.isfinite(array)]

                if finite.size == 0:
                    return None

                return DatasetUploadService._json_safe_value(
                    finite.min()
                )

            return DatasetUploadService._json_safe_value(
                array.min()
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

    @staticmethod
    def _safe_max(values):
        """Return a JSON-safe maximum value."""

        try:
            array = np.asarray(values)

            if array.size == 0:
                return None

            if np.issubdtype(
                array.dtype,
                np.datetime64,
            ):
                return str(array.max())

            if np.issubdtype(
                array.dtype,
                np.number,
            ):
                finite = array[np.isfinite(array)]

                if finite.size == 0:
                    return None

                return DatasetUploadService._json_safe_value(
                    finite.max()
                )

            return DatasetUploadService._json_safe_value(
                array.max()
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None