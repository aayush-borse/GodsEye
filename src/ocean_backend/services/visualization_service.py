"""Backend services that prepare ocean data for 3D visualization."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import xarray as xr

from ocean_backend.services.upload_service import DatasetNotFoundError, DatasetRegistry


class VisualizationDataError(Exception):
    """Raised when data cannot be prepared for visualization."""


class VisualizationService:
    """Prepare bounded, renderer-friendly model data."""

    MAX_VALUES = 250_000
    MAX_VECTOR_POINTS = 20_000

    VARIABLE_ALIASES = {
        "temperature": "thetao",
        "temp": "thetao",
        "salinity": "so",
        "u": "uo",
        "eastward_velocity": "uo",
        "eastward_current": "uo",
        "v": "vo",
        "northward_velocity": "vo",
        "northward_current": "vo",
        "w": "wo",
        "vertical_velocity": "wo",
    }

    LOD_STRIDES = {
        "preview": 4,
        "balanced": 2,
        "full": 1,
    }

    def __init__(self, registry: DatasetRegistry) -> None:
        self.registry = registry

    def manifest(self, dataset_id: str) -> dict[str, Any]:
        dataset = self._get_dataset(dataset_id)

        capabilities = {
            "volume": False,
            "horizontal_slice": False,
            "vectors": False,
            "point_query": False,
        }

        for name, data_array in dataset.data_vars.items():
            dims = {dim.lower() for dim in data_array.dims}
            if {"latitude", "longitude", "lat", "lon"} & dims and "depth" in dims:
                capabilities["volume"] = True
                capabilities["horizontal_slice"] = True
            if self._has_xy_dims(data_array) and ("uo" in dataset or "vo" in dataset):
                capabilities["vectors"] = True
            capabilities["point_query"] = True

        variables = []
        for name, data_array in dataset.data_vars.items():
            variables.append(
                {
                    "name": name,
                    "dimensions": list(data_array.dims),
                    "shape": [int(size) for size in data_array.shape],
                    "dtype": str(data_array.dtype),
                    "units": str(data_array.attrs.get("units", "")),
                    "long_name": str(data_array.attrs.get("long_name", name)),
                }
            )

        return {
            "dataset_id": dataset_id,
            "dimensions": {name: int(size) for name, size in dataset.sizes.items()},
            "coordinates": self._coordinate_summary(dataset),
            "variables": variables,
            "aliases": self.VARIABLE_ALIASES,
            "capabilities": capabilities,
            "limits": {
                "max_volume_values": self.MAX_VALUES,
                "max_vector_points": self.MAX_VECTOR_POINTS,
                "lod": self.LOD_STRIDES,
            },
        }

    def volume_binary(
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
        stride: int | None = None,
        lod: str | None = None,
    ) -> tuple[bytes, dict[str, Any]]:
        dataset = self._get_dataset(dataset_id)
        variable_name = self.resolve_variable(dataset, variable)
        data = self._select_volume(
            dataset,
            variable_name,
            time_index,
            depth_min,
            depth_max,
            latitude_min,
            latitude_max,
            longitude_min,
            longitude_max,
        )

        selected_stride = self._resolve_stride(data, stride, lod)
        data = self._apply_spatial_stride(data, selected_stride)
        self._validate_3d(data, variable_name)
        self._validate_size(data.size, self.MAX_VALUES)

        array = np.asarray(data.values, dtype="<f4")
        array = np.ascontiguousarray(array)
        coords = self._coords_for(data)

        metadata = {
            "dataset_id": dataset_id,
            "variable": variable,
            "model_variable": variable_name,
            "dimensions": list(data.dims),
            "shape": [int(size) for size in array.shape],
            "coordinates": coords,
            "stride": selected_stride,
            "value_count": int(array.size),
            "min": self._finite_min(array),
            "max": self._finite_max(array),
            "nan_count": int(np.isnan(array).sum()),
            "dtype": "float32",
            "byte_order": "little-endian",
        }
        return array.tobytes(), metadata

    def slice_binary(
        self,
        dataset_id: str,
        variable: str,
        depth: float,
        time_index: int = 0,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        stride: int = 1,
    ) -> tuple[bytes, dict[str, Any]]:
        dataset = self._get_dataset(dataset_id)
        variable_name = self.resolve_variable(dataset, variable)
        data = self._select_volume(
            dataset,
            variable_name,
            time_index,
            None,
            None,
            latitude_min,
            latitude_max,
            longitude_min,
            longitude_max,
        )
        self._validate_3d(data, variable_name)
        data = data.sel(depth=depth, method="nearest")
        selected_depth = float(np.asarray(data.coords["depth"].values))
        data = self._apply_spatial_stride(data, max(1, stride))
        self._validate_size(data.size, self.MAX_VALUES)

        array = np.asarray(data.values, dtype="<f4")
        array = np.ascontiguousarray(array)
        metadata = {
            "dataset_id": dataset_id,
            "variable": variable,
            "model_variable": variable_name,
            "dimensions": list(data.dims),
            "shape": [int(size) for size in array.shape],
            "coordinates": self._coords_for(data),
            "requested_depth": float(depth),
            "selected_depth": selected_depth,
            "stride": max(1, stride),
            "value_count": int(array.size),
            "min": self._finite_min(array),
            "max": self._finite_max(array),
            "dtype": "float32",
            "byte_order": "little-endian",
        }
        return array.tobytes(), metadata

    def vector_binary(
        self,
        dataset_id: str,
        time_index: int = 0,
        depth: float | None = None,
        latitude_min: float | None = None,
        latitude_max: float | None = None,
        longitude_min: float | None = None,
        longitude_max: float | None = None,
        stride: int = 1,
    ) -> tuple[bytes, dict[str, Any]]:
        """Return interleaved U/V(/W) vectors for glyph rendering."""

        dataset = self._get_dataset(dataset_id)
        u_name = self._find_first(dataset, ("uo", "u", "eastward_velocity"))
        v_name = self._find_first(dataset, ("vo", "v", "northward_velocity"))
        if not u_name or not v_name:
            raise VisualizationDataError("Dataset must contain both U and V current components.")

        u = self._select_volume(
            dataset, u_name, time_index, None, None,
            latitude_min, latitude_max, longitude_min, longitude_max,
        )
        v = self._select_volume(
            dataset, v_name, time_index, None, None,
            latitude_min, latitude_max, longitude_min, longitude_max,
        )
        self._validate_3d(u, u_name)
        self._validate_3d(v, v_name)

        if depth is not None:
            u = u.sel(depth=depth, method="nearest")
            v = v.sel(depth=depth, method="nearest")
            selected_depth = float(np.asarray(u.coords["depth"].values))
        else:
            # A vector glyph layer without a selected depth becomes too large.
            # Use the shallowest model level as the safe default.
            u = u.isel(depth=0)
            v = v.isel(depth=0)
            selected_depth = float(np.asarray(u.coords["depth"].values))

        stride = max(1, stride)
        u = self._apply_spatial_stride(u, stride)
        v = self._apply_spatial_stride(v, stride)

        if u.shape != v.shape:
            raise VisualizationDataError("U and V current components do not share the same grid.")

        u_values = np.asarray(u.values, dtype="<f4")
        v_values = np.asarray(v.values, dtype="<f4")
        finite = np.isfinite(u_values) & np.isfinite(v_values)
        point_count = int(u_values.size)
        self._validate_size(point_count, self.MAX_VECTOR_POINTS)

        # Interleaved U,V values make the browser upload cheap and predictable.
        vectors = np.empty((point_count, 2), dtype="<f4")
        vectors[:, 0] = u_values.reshape(-1)
        vectors[:, 1] = v_values.reshape(-1)
        vectors[~finite.reshape(-1)] = np.nan
        vectors = np.ascontiguousarray(vectors)

        metadata = {
            "dataset_id": dataset_id,
            "u_variable": u_name,
            "v_variable": v_name,
            "dimensions": list(u.dims),
            "shape": [int(size) for size in u.shape],
            "coordinates": self._coords_for(u),
            "selected_depth": selected_depth,
            "stride": stride,
            "point_count": point_count,
            "valid_point_count": int(finite.sum()),
            "components": 2,
            "layout": "interleaved_uv",
            "dtype": "float32",
            "byte_order": "little-endian",
        }
        return vectors.tobytes(), metadata

    def point_query(
        self,
        dataset_id: str,
        latitude: float,
        longitude: float,
        depth: float,
        time_index: int = 0,
        variable: str = "temperature",
    ) -> dict[str, Any]:
        dataset = self._get_dataset(dataset_id)
        variable_name = self.resolve_variable(dataset, variable)
        data = self._select_time(self._get_variable(dataset, variable_name), time_index)
        if "depth" not in data.dims:
            raise VisualizationDataError(f"Variable '{variable_name}' has no depth dimension.")
        try:
            selected = data.sel(
                latitude=latitude,
                longitude=longitude,
                depth=depth,
                method="nearest",
            )
        except Exception as exc:
            try:
                selected = data.sel(
                    lat=latitude,
                    lon=longitude,
                    depth=depth,
                    method="nearest",
                )
            except Exception as inner_exc:
                raise VisualizationDataError("Dataset does not expose a regular lat/lon/depth grid.") from inner_exc

        value = float(np.asarray(selected.values))
        actual_lat = self._coord_scalar(selected, ("latitude", "lat"))
        actual_lon = self._coord_scalar(selected, ("longitude", "lon"))
        actual_depth = self._coord_scalar(selected, ("depth",))
        return {
            "dataset_id": dataset_id,
            "variable": variable,
            "model_variable": variable_name,
            "requested": {
                "latitude": latitude,
                "longitude": longitude,
                "depth": depth,
                "time_index": time_index,
            },
            "selected": {
                "latitude": actual_lat,
                "longitude": actual_lon,
                "depth": actual_depth,
                "value": value if math.isfinite(value) else None,
            },
        }

    def resolve_variable(self, dataset: xr.Dataset, variable: str) -> str:
        key = str(variable).strip()
        if key in dataset.data_vars:
            return key
        alias = self.VARIABLE_ALIASES.get(key.lower())
        if alias and alias in dataset.data_vars:
            return alias
        raise VisualizationDataError(
            f"Variable '{variable}' is not available. Dataset variables: {', '.join(dataset.data_vars)}."
        )

    def _get_dataset(self, dataset_id: str) -> xr.Dataset:
        try:
            return self.registry.get(dataset_id)
        except DatasetNotFoundError:
            raise

    @staticmethod
    def _get_variable(dataset: xr.Dataset, variable: str) -> xr.DataArray:
        if variable not in dataset.data_vars:
            raise VisualizationDataError(f"Variable '{variable}' is not available in this dataset.")
        return dataset[variable]

    @staticmethod
    def _select_time(data: xr.DataArray, time_index: int) -> xr.DataArray:
        if "time" not in data.dims:
            return data
        if time_index < 0 or time_index >= data.sizes["time"]:
            raise VisualizationDataError(
                f"time_index {time_index} is outside the dataset time range 0..{data.sizes['time'] - 1}."
            )
        return data.isel(time=time_index)

    def _select_volume(
        self,
        dataset: xr.Dataset,
        variable: str,
        time_index: int,
        depth_min: float | None,
        depth_max: float | None,
        latitude_min: float | None,
        latitude_max: float | None,
        longitude_min: float | None,
        longitude_max: float | None,
    ) -> xr.DataArray:
        data = self._select_time(self._get_variable(dataset, variable), time_index)
        for name, minimum, maximum in (
            ("depth", depth_min, depth_max),
            ("latitude", latitude_min, latitude_max),
            ("longitude", longitude_min, longitude_max),
        ):
            coordinate_name = self._resolve_coordinate(data, name)
            if coordinate_name is None or (minimum is None and maximum is None):
                continue
            coordinate = data.coords[coordinate_name]
            if coordinate.ndim != 1:
                raise VisualizationDataError(
                    f"3D visualization currently requires one-dimensional {name} coordinates."
                )
            lo = minimum if minimum is not None else float(np.nanmin(coordinate.values))
            hi = maximum if maximum is not None else float(np.nanmax(coordinate.values))
            if lo > hi:
                raise VisualizationDataError(f"{name}_min cannot be greater than {name}_max.")
            data = data.sel({coordinate_name: slice(lo, hi)})
        return self._canonicalize_3d(data)

    @staticmethod
    def _canonicalize_3d(data: xr.DataArray) -> xr.DataArray:
        """Return a predictable depth, latitude, longitude dimension order."""
        depth = next((name for name in ("depth", "deptht", "lev", "level") if name in data.dims), None)
        latitude = next((name for name in ("latitude", "lat") if name in data.dims), None)
        longitude = next((name for name in ("longitude", "lon") if name in data.dims), None)
        if not (depth and latitude and longitude):
            return data
        return data.transpose(depth, latitude, longitude)

    @staticmethod
    def _resolve_coordinate(data: xr.DataArray, name: str) -> str | None:
        aliases = {
            "latitude": ("latitude", "lat"),
            "longitude": ("longitude", "lon"),
            "depth": ("depth", "deptht", "lev", "level"),
        }
        for candidate in aliases[name]:
            if candidate in data.coords or candidate in data.dims:
                return candidate
        return None

    def _apply_spatial_stride(self, data: xr.DataArray, stride: int) -> xr.DataArray:
        for coordinate_name in ("depth", "deptht", "lev", "level", "latitude", "lat", "longitude", "lon"):
            if coordinate_name in data.dims:
                data = data.isel({coordinate_name: slice(None, None, stride)})
        return data

    def _resolve_stride(self, data: xr.DataArray, stride: int | None, lod: str | None) -> int:
        if stride is not None:
            if stride < 1 or stride > 20:
                raise VisualizationDataError("stride must be between 1 and 20.")
            return stride
        if lod:
            normalized = lod.strip().lower()
            if normalized not in self.LOD_STRIDES:
                raise VisualizationDataError("lod must be preview, balanced or full.")
            return self.LOD_STRIDES[normalized]
        return 2

    @staticmethod
    def _validate_3d(data: xr.DataArray, variable: str) -> None:
        has_depth = any(name in data.dims for name in ("depth", "deptht", "lev", "level"))
        has_lat = any(name in data.dims for name in ("latitude", "lat"))
        has_lon = any(name in data.dims for name in ("longitude", "lon"))
        if not (has_depth and has_lat and has_lon):
            raise VisualizationDataError(
                f"Variable '{variable}' must have depth, latitude and longitude dimensions for 3D rendering."
            )

    @staticmethod
    def _validate_size(size: int, maximum: int) -> None:
        if size > maximum:
            raise VisualizationDataError(
                f"Requested visualization payload has {size} values; maximum is {maximum}. Increase stride."
            )

    @staticmethod
    def _has_xy_dims(data: xr.DataArray) -> bool:
        dims = set(data.dims)
        return bool(dims & {"latitude", "lat"}) and bool(dims & {"longitude", "lon"})

    @staticmethod
    def _find_first(dataset: xr.Dataset, names: tuple[str, ...]) -> str | None:
        lowered = {name.lower(): name for name in dataset.data_vars}
        for candidate in names:
            if candidate.lower() in lowered:
                return lowered[candidate.lower()]
        return None

    @staticmethod
    def _coord_scalar(data: xr.DataArray, names: tuple[str, ...]) -> float:
        for name in names:
            if name in data.coords:
                return float(np.asarray(data.coords[name].values))
        raise VisualizationDataError(f"Coordinate {names[0]} not found.")

    @staticmethod
    def _finite_min(array: np.ndarray) -> float | None:
        finite = array[np.isfinite(array)]
        return float(finite.min()) if finite.size else None

    @staticmethod
    def _finite_max(array: np.ndarray) -> float | None:
        finite = array[np.isfinite(array)]
        return float(finite.max()) if finite.size else None

    @staticmethod
    def _coords_for(data: xr.DataArray) -> dict[str, list[Any]]:
        result: dict[str, list[Any]] = {}
        for name in data.dims:
            if name not in data.coords:
                continue
            coordinate = data.coords[name]
            if coordinate.ndim != 1:
                continue
            values = coordinate.values
            if np.issubdtype(values.dtype, np.datetime64):
                result[name] = [str(value) for value in values]
            else:
                result[name] = [float(value) for value in values]
        return result

    @staticmethod
    def _coordinate_summary(dataset: xr.Dataset) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for public_name, aliases in {
            "latitude": ("latitude", "lat"),
            "longitude": ("longitude", "lon"),
            "depth": ("depth", "deptht", "lev", "level"),
            "time": ("time",),
        }.items():
            for name in aliases:
                if name not in dataset.coords:
                    continue
                coordinate = dataset.coords[name]
                if coordinate.ndim != 1:
                    continue
                values = coordinate.values
                if np.issubdtype(values.dtype, np.datetime64):
                    result[public_name] = {
                        "name": name,
                        "count": int(values.size),
                        "values": [str(value) for value in values],
                    }
                else:
                    result[public_name] = {
                        "name": name,
                        "count": int(values.size),
                        "min": float(np.nanmin(values)),
                        "max": float(np.nanmax(values)),
                    }
                break
        return result
