"""Scientific data access for uploaded xarray datasets."""

from __future__ import annotations

from typing import Any

import numpy as np
import xarray as xr

from ocean_backend.models.datasets import (
    CoordinateAxis,
    DatasetCoordinateMetadataResponse,
    DatasetDataResponse,
    DatasetSliceResponse,
    DatasetVolumeResponse,
)
from ocean_backend.services.upload_service import (
    DatasetNotFoundError,
    DatasetRegistry,
)


class DatasetDataError(Exception):
    """Raised when requested dataset data cannot be returned."""


class DatasetDataService:
    """Provides controlled access to uploaded xarray datasets."""

    # ----------------------------------------------------------
    # JSON safety limit.
    #
    # Binary endpoints are intended for visualization, while the
    # JSON endpoints remain useful for inspection and debugging.
    # ----------------------------------------------------------

    MAX_RESPONSE_VALUES = 100_000

    def __init__(self, registry: DatasetRegistry) -> None:
        self.registry = registry

    def get_data(
        self,
        dataset_id: str,
        variable: str,
        time_index: int = 0,
        depth_min: float | None = None,
        depth_max: float | None = None,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        depth_stride: int = 1,
        latitude_stride: int = 1,
        longitude_stride: int = 1,
    ) -> DatasetDataResponse:
        """Return a selected portion of a dataset variable."""

        data_array = self._prepare_data_array(
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

        self._validate_response_size(data_array)

        return self._build_data_response(
            dataset_id=dataset_id,
            variable=variable,
            data_array=data_array,
        )

    def get_slice(
        self,
        dataset_id: str,
        variable: str,
        depth: float,
        time_index: int = 0,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        latitude_stride: int = 1,
        longitude_stride: int = 1,
    ) -> DatasetSliceResponse:
        """Return the horizontal slice nearest to a requested depth."""

        dataset = self._get_dataset(dataset_id)

        data_array = self._get_variable(
            dataset,
            variable,
        )

        data_array = self._select_time(
            data_array,
            time_index,
        )

        if "depth" not in data_array.dims:
            raise DatasetDataError(
                f"Variable '{variable}' does not contain a depth dimension."
            )

        # Select the model level closest to the requested depth.
        data_array = data_array.sel(
            depth=depth,
            method="nearest",
        )

        selected_depth = float(
            np.asarray(
                data_array.coords["depth"].values,
            )
        )

        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="latitude",
            minimum=latitude_min,
            maximum=latitude_max,
        )

        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="longitude",
            minimum=longitude_min,
            maximum=longitude_max,
        )

        data_array = self._apply_stride(
            data_array,
            coordinate_name="latitude",
            stride=latitude_stride,
        )

        data_array = self._apply_stride(
            data_array,
            coordinate_name="longitude",
            stride=longitude_stride,
        )

        if "latitude" not in data_array.dims:
            raise DatasetDataError(
                "Selected slice does not contain a latitude dimension."
            )

        if "longitude" not in data_array.dims:
            raise DatasetDataError(
                "Selected slice does not contain a longitude dimension."
            )

        self._validate_response_size(data_array)

        response = self._build_data_response(
            dataset_id=dataset_id,
            variable=variable,
            data_array=data_array,
        )

        return DatasetSliceResponse(
            dataset_id=response.dataset_id,
            variable=response.variable,
            depth=selected_depth,
            dimensions=response.dimensions,
            shape=response.shape,
            coordinates=response.coordinates,
            values=response.values,
        )

    def get_slice_binary(
        self,
        dataset_id: str,
        variable: str,
        depth: float,
        time_index: int = 0,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        latitude_stride: int = 1,
        longitude_stride: int = 1,
    ) -> tuple[bytes, tuple[int, ...], float]:
        """
        Return a horizontal depth slice as float32 binary data.

        The returned tuple contains:

        - raw binary bytes
        - array shape
        - actual model depth selected
        """

        dataset = self._get_dataset(
            dataset_id,
        )

        data_array = self._get_variable(
            dataset,
            variable,
        )

        data_array = self._select_time(
            data_array,
            time_index,
        )

        if "depth" not in data_array.dims:
            raise DatasetDataError(
                f"Variable '{variable}' does not contain a depth dimension."
            )

        # Select the nearest available model depth.
        data_array = data_array.sel(
            depth=depth,
            method="nearest",
        )

        selected_depth = float(
            np.asarray(
                data_array.coords["depth"].values,
            )
        )

        # Restrict geographic bounds before materializing values.
        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="latitude",
            minimum=latitude_min,
            maximum=latitude_max,
        )

        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="longitude",
            minimum=longitude_min,
            maximum=longitude_max,
        )

        # Downsample the horizontal grid when requested.
        data_array = self._apply_stride(
            data_array,
            coordinate_name="latitude",
            stride=latitude_stride,
        )

        data_array = self._apply_stride(
            data_array,
            coordinate_name="longitude",
            stride=longitude_stride,
        )

        if "latitude" not in data_array.dims:
            raise DatasetDataError(
                "Selected slice does not contain a latitude dimension."
            )

        if "longitude" not in data_array.dims:
            raise DatasetDataError(
                "Selected slice does not contain a longitude dimension."
            )

        self._validate_response_size(
            data_array,
        )

        # ------------------------------------------------------
        # Convert directly to float32.
        #
        # This avoids the Python list + JSON serialization path.
        # NaN values are preserved because Float32Array supports
        # them on the frontend.
        # ------------------------------------------------------

        array = np.asarray(
            data_array.values,
            dtype=np.float32,
        )

        array = np.ascontiguousarray(
            array,
        )

        return (
            array.tobytes(),
            tuple(
                int(size)
                for size in array.shape
            ),
            selected_depth,
        )

    def get_volume(
        self,
        dataset_id: str,
        variable: str,
        time_index: int = 0,
        depth_min: float | None = None,
        depth_max: float | None = None,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        depth_stride: int = 1,
        latitude_stride: int = 1,
        longitude_stride: int = 1,
    ) -> DatasetVolumeResponse:
        """Return a controlled three-dimensional variable volume."""

        response = self.get_data(
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

        if "depth" not in response.dimensions:
            raise DatasetDataError(
                f"Variable '{variable}' does not contain a depth dimension."
            )

        return DatasetVolumeResponse(
            dataset_id=response.dataset_id,
            variable=response.variable,
            dimensions=response.dimensions,
            shape=response.shape,
            coordinates=response.coordinates,
            values=response.values,
        )

    def get_volume_binary(
        self,
        dataset_id: str,
        variable: str,
        time_index: int = 0,
        depth_min: float | None = None,
        depth_max: float | None = None,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        depth_stride: int = 1,
        latitude_stride: int = 1,
        longitude_stride: int = 1,
    ) -> tuple[bytes, tuple[int, ...]]:
        """Return a selected volume as contiguous float32 binary data."""

        data_array = self._prepare_data_array(
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

        if "depth" not in data_array.dims:
            raise DatasetDataError(
                f"Variable '{variable}' does not contain a depth dimension."
            )

        self._validate_response_size(
            data_array,
        )

        array = np.asarray(
            data_array.values,
            dtype=np.float32,
        )

        array = np.ascontiguousarray(
            array,
        )

        return (
            array.tobytes(),
            tuple(
                int(size)
                for size in array.shape
            ),
        )

    def get_coordinate_metadata(
        self,
        dataset_id: str,
    ) -> DatasetCoordinateMetadataResponse:
        """
        Return coordinate information required to position the dataset.

        The frontend uses this information to map array indices to
        real latitude, longitude, depth, and time coordinates.
        """

        dataset = self._get_dataset(dataset_id)

        latitude = self._build_coordinate_axis(
            dataset=dataset,
            coordinate_names=("latitude", "lat"),
            axis_name="latitude",
        )

        longitude = self._build_coordinate_axis(
            dataset=dataset,
            coordinate_names=("longitude", "lon"),
            axis_name="longitude",
        )

        depth = self._build_coordinate_axis(
            dataset=dataset,
            coordinate_names=("depth", "deptht", "lev", "level"),
            axis_name="depth",
        )

        time_values: list[Any] = []

        if "time" in dataset.coords:
            time_values = self._convert_values(
                dataset.coords["time"].values,
            )

        return DatasetCoordinateMetadataResponse(
            dataset_id=dataset_id,
            latitude=latitude,
            longitude=longitude,
            depth=depth,
            time=time_values,
        )

    @classmethod
    def _build_coordinate_axis(
        cls,
        dataset: xr.Dataset,
        coordinate_names: tuple[str, ...],
        axis_name: str,
    ) -> CoordinateAxis | None:
        """Build metadata for the first matching coordinate."""

        coordinate_name = next(
            (
                name
                for name in coordinate_names
                if name in dataset.coords
            ),
            None,
        )

        if coordinate_name is None:
            return None

        coordinate = dataset.coords[coordinate_name]

        values = np.asarray(
            coordinate.values,
        ).reshape(-1)

        if values.size == 0:
            return None

        if not np.issubdtype(
            values.dtype,
            np.number,
        ):
            raise DatasetDataError(
                f"Coordinate '{coordinate_name}' is not numeric."
            )

        finite_values = values[
            np.isfinite(values)
        ]

        if finite_values.size == 0:
            raise DatasetDataError(
                f"Coordinate '{coordinate_name}' contains no finite values."
            )

        return CoordinateAxis(
            name=axis_name,
            min_value=float(
                np.min(finite_values),
            ),
            max_value=float(
                np.max(finite_values),
            ),
            count=int(values.size),
            values=[
                float(value)
                for value in values
            ],
        )

    def _prepare_data_array(
        self,
        dataset_id: str,
        variable: str,
        time_index: int,
        depth_min: float | None,
        depth_max: float | None,
        latitude_min: float | None,
        latitude_max: float | None,
        longitude_min: float | None,
        longitude_max: float | None,
        depth_stride: int,
        latitude_stride: int,
        longitude_stride: int,
    ) -> xr.DataArray:
        """Select and sample a dataset without converting it to JSON."""

        dataset = self._get_dataset(
            dataset_id,
        )

        data_array = self._get_variable(
            dataset,
            variable,
        )

        data_array = self._select_time(
            data_array,
            time_index,
        )

        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="depth",
            minimum=depth_min,
            maximum=depth_max,
        )

        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="latitude",
            minimum=latitude_min,
            maximum=latitude_max,
        )

        data_array = self._select_coordinate_range(
            data_array,
            coordinate_name="longitude",
            minimum=longitude_min,
            maximum=longitude_max,
        )

        data_array = self._apply_stride(
            data_array,
            coordinate_name="depth",
            stride=depth_stride,
        )

        data_array = self._apply_stride(
            data_array,
            coordinate_name="latitude",
            stride=latitude_stride,
        )

        data_array = self._apply_stride(
            data_array,
            coordinate_name="longitude",
            stride=longitude_stride,
        )

        return data_array

    def _get_dataset(
        self,
        dataset_id: str,
    ) -> xr.Dataset:
        """Retrieve a dataset from the shared runtime registry."""

        try:
            return self.registry.get(
                dataset_id,
            )

        except DatasetNotFoundError:
            raise

    @staticmethod
    def _get_variable(
        dataset: xr.Dataset,
        variable: str,
    ) -> xr.DataArray:
        """Retrieve and validate a dataset variable."""

        if variable not in dataset.data_vars:
            available = ", ".join(
                dataset.data_vars,
            )

            raise DatasetDataError(
                f"Variable '{variable}' was not found. "
                f"Available variables: {available}"
            )

        data_array = dataset[variable]

        if data_array.size == 0:
            raise DatasetDataError(
                f"Variable '{variable}' contains no data."
            )

        return data_array

    @staticmethod
    def _select_time(
        data_array: xr.DataArray,
        time_index: int,
    ) -> xr.DataArray:
        """Select one time step when a time dimension exists."""

        if "time" not in data_array.dims:
            return data_array

        time_size = data_array.sizes["time"]

        if time_index < 0 or time_index >= time_size:
            raise DatasetDataError(
                f"time_index {time_index} is outside the "
                f"available range 0-{time_size - 1}."
            )

        return data_array.isel(
            time=time_index,
        )

    @staticmethod
    def _select_coordinate_range(
        data_array: xr.DataArray,
        coordinate_name: str,
        minimum: float | None,
        maximum: float | None,
    ) -> xr.DataArray:
        """Restrict a variable to a coordinate range."""

        if minimum is None and maximum is None:
            return data_array

        if coordinate_name not in data_array.coords:
            raise DatasetDataError(
                f"Dataset does not contain a "
                f"'{coordinate_name}' coordinate."
            )

        coordinate = data_array.coords[
            coordinate_name
        ]

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise DatasetDataError(
                    f"{coordinate_name}_min cannot be greater than "
                    f"{coordinate_name}_max."
                )

            return data_array.sel(
                {
                    coordinate_name: slice(
                        minimum,
                        maximum,
                    )
                }
            )

        if minimum is not None:
            return data_array.sel(
                {
                    coordinate_name: coordinate[
                        coordinate >= minimum
                    ]
                }
            )

        return data_array.sel(
            {
                coordinate_name: coordinate[
                    coordinate <= maximum
                ]
            }
        )

    @staticmethod
    def _apply_stride(
        data_array: xr.DataArray,
        coordinate_name: str,
        stride: int,
    ) -> xr.DataArray:
        """Apply a sampling stride to one dimension."""

        if stride < 1:
            raise DatasetDataError(
                f"{coordinate_name}_stride must be at least 1."
            )

        if coordinate_name not in data_array.dims:
            return data_array

        return data_array.isel(
            {
                coordinate_name: slice(
                    None,
                    None,
                    stride,
                )
            }
        )

    @classmethod
    def _validate_response_size(
        cls,
        data_array: xr.DataArray,
    ) -> None:
        """Reject oversized responses before materializing values."""

        value_count = int(
            data_array.size,
        )

        if value_count > cls.MAX_RESPONSE_VALUES:
            raise DatasetDataError(
                "Requested dataset region is too large. "
                f"It contains {value_count} values, while the maximum "
                f"response size is {cls.MAX_RESPONSE_VALUES}. "
                "Increase the spatial/depth stride or reduce the "
                "requested geographic/depth range."
            )

    @classmethod
    def _build_data_response(
        cls,
        dataset_id: str,
        variable: str,
        data_array: xr.DataArray,
    ) -> DatasetDataResponse:
        """Build the JSON response from a selected xarray array."""

        values = cls._convert_values(
            data_array.values,
        )

        coordinates: dict[str, list[Any]] = {}

        for name in data_array.dims:
            if name not in data_array.coords:
                continue

            coordinates[name] = cls._convert_values(
                data_array.coords[name].values,
            )

        return DatasetDataResponse(
            dataset_id=dataset_id,
            variable=variable,
            dimensions=list(data_array.dims),
            shape=[
                int(size)
                for size in data_array.shape
            ],
            coordinates=coordinates,
            values=values,
        )

    @staticmethod
    def _convert_values(
        values,
    ) -> list[Any]:
        """Convert NumPy/xarray values into JSON-safe Python values."""

        array = np.asarray(
            values,
        )

        if np.issubdtype(
            array.dtype,
            np.datetime64,
        ):
            return [
                str(value)
                for value in array.reshape(-1)
            ]

        if array.dtype.kind in {
            "U",
            "S",
        }:
            return [
                str(value)
                for value in array.reshape(-1)
            ]

        if np.issubdtype(
            array.dtype,
            np.number,
        ):
            result = array.astype(
                object,
                copy=True,
            )

            result[
                ~np.isfinite(array)
            ] = None

            return result.reshape(-1).tolist()

        return array.reshape(-1).tolist()