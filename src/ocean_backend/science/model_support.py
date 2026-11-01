"""Validation of whether a model dataset can support a scientific comparison."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import xarray as xr


@dataclass(frozen=True)
class ModelSupport:
    """Describes whether a model can support a requested comparison."""

    supported: bool

    variable_supported: bool
    latitude_supported: bool
    longitude_supported: bool
    depth_supported: bool
    time_supported: bool
    data_available: bool

    reasons: list[str]


class ModelSupportValidator:
    """
    Validate model support for a requested latitude, longitude,
    depth, time, and variable.

    This class does not perform interpolation or comparison.
    It only determines whether the model contains sufficient
    information for those operations.
    """

    def __init__(self, dataset: xr.Dataset) -> None:
        self.dataset = dataset

    def validate(
        self,
        *,
        latitude: float,
        longitude: float,
        depth: float,
        time: datetime | np.datetime64,
        variable: str,
    ) -> ModelSupport:
        reasons: list[str] = []

        variable_supported = self._check_variable(variable, reasons)

        latitude_supported = self._check_latitude(latitude, reasons)

        longitude_supported = self._check_longitude(longitude, reasons)

        depth_supported = self._check_depth(depth, reasons)

        time_supported = self._check_time(time, reasons)

        data_available = False

        if (
            variable_supported
            and latitude_supported
            and longitude_supported
            and depth_supported
            and time_supported
        ):
            data_available = self._check_data_availability(
                latitude=latitude,
                longitude=longitude,
                depth=depth,
                time=time,
                variable=variable,
                reasons=reasons,
            )

        supported = (
            variable_supported
            and latitude_supported
            and longitude_supported
            and depth_supported
            and time_supported
            and data_available
        )

        return ModelSupport(
            supported=supported,
            variable_supported=variable_supported,
            latitude_supported=latitude_supported,
            longitude_supported=longitude_supported,
            depth_supported=depth_supported,
            time_supported=time_supported,
            data_available=data_available,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Variable
    # ------------------------------------------------------------------

    def _check_variable(
        self,
        variable: str,
        reasons: list[str],
    ) -> bool:
        if not variable or not variable.strip():
            reasons.append("Model variable cannot be empty.")
            return False

        if variable not in self.dataset.data_vars:
            reasons.append(
                f"Variable '{variable}' is not available in the model dataset."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Latitude
    # ------------------------------------------------------------------

    def _check_latitude(
        self,
        latitude: float,
        reasons: list[str],
    ) -> bool:
        if not np.isfinite(latitude):
            reasons.append("Requested latitude is not finite.")
            return False

        latitude_values = self._coordinate_values(
            names=("latitude", "lat"),
        )

        if latitude_values is None:
            reasons.append(
                "Model dataset does not contain a recognizable latitude coordinate."
            )
            return False

        minimum = float(np.nanmin(latitude_values))
        maximum = float(np.nanmax(latitude_values))

        if latitude < minimum or latitude > maximum:
            reasons.append(
                f"Requested latitude {latitude}° is outside "
                f"model range [{minimum}°, {maximum}°]."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Longitude
    # ------------------------------------------------------------------

    def _check_longitude(
        self,
        longitude: float,
        reasons: list[str],
    ) -> bool:
        if not np.isfinite(longitude):
            reasons.append("Requested longitude is not finite.")
            return False

        longitude_values = self._coordinate_values(
            names=("longitude", "lon"),
        )

        if longitude_values is None:
            reasons.append(
                "Model dataset does not contain a recognizable longitude coordinate."
            )
            return False

        minimum = float(np.nanmin(longitude_values))
        maximum = float(np.nanmax(longitude_values))

        if longitude < minimum or longitude > maximum:
            reasons.append(
                f"Requested longitude {longitude}° is outside "
                f"model range [{minimum}°, {maximum}°]."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Depth
    # ------------------------------------------------------------------

    def _check_depth(
        self,
        depth: float,
        reasons: list[str],
    ) -> bool:
        if not np.isfinite(depth):
            reasons.append("Requested depth is not finite.")
            return False

        if depth < 0:
            reasons.append(
                f"Requested depth {depth} m is invalid. "
                "Ocean depth cannot be negative."
            )
            return False

        depth_values = self._coordinate_values(
            names=("depth", "depth_m", "lev", "level", "z"),
        )

        if depth_values is None:
            reasons.append(
                "Model dataset does not contain a recognizable depth coordinate."
            )
            return False

        minimum = float(np.nanmin(depth_values))
        maximum = float(np.nanmax(depth_values))

        if depth < minimum or depth > maximum:
            reasons.append(
                f"Requested depth {depth} m exceeds model-supported "
                f"range [{minimum} m, {maximum} m]."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------

    def _check_time(
        self,
        requested_time: datetime | np.datetime64,
        reasons: list[str],
    ) -> bool:
        try:
            requested = self._to_datetime64(requested_time)
        except (TypeError, ValueError):
            reasons.append("Requested time is invalid.")
            return False

        time_values = self._coordinate_values(
            names=("time",),
        )

        if time_values is None:
            reasons.append(
                "Model dataset does not contain a recognizable time coordinate."
            )
            return False

        try:
            model_times = np.asarray(time_values, dtype="datetime64[ns]")

            if np.isnat(model_times).all():
                reasons.append("Model dataset contains no valid time values.")
                return False

            minimum = model_times[~np.isnat(model_times)].min()
            maximum = model_times[~np.isnat(model_times)].max()

        except (TypeError, ValueError):
            reasons.append("Model time coordinate could not be interpreted.")
            return False

        if requested < minimum or requested > maximum:
            reasons.append(
                f"Requested time {requested} is outside model time range "
                f"[{minimum}, {maximum}]."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Data availability
    # ------------------------------------------------------------------

    def _check_data_availability(
        self,
        *,
        latitude: float,
        longitude: float,
        depth: float,
        time: datetime | np.datetime64,
        variable: str,
        reasons: list[str],
    ) -> bool:
        """
        Check whether the requested point can produce a finite model value.

        This deliberately uses nearest-neighbour selection only for the
        availability check. Actual interpolation remains the responsibility
        of the interpolation/scientific layer.
        """

        try:
            selection = self._nearest_selection(
                latitude=latitude,
                longitude=longitude,
                depth=depth,
                time=time,
                variable=variable,
            )

            value = selection.item()

        except (KeyError, ValueError, IndexError, TypeError):
            reasons.append(
                "No model data could be resolved at the requested location, "
                "depth, and time."
            )
            return False

        try:
            if not np.isfinite(float(value)):
                reasons.append(
                    "Model data is unavailable or invalid at the requested point."
                )
                return False
        except (TypeError, ValueError):
            reasons.append(
                "Model value at the requested point is not numeric."
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _coordinate_values(
        self,
        *,
        names: tuple[str, ...],
    ) -> np.ndarray | None:
        for name in names:
            if name in self.dataset.coords:
                values = self.dataset.coords[name].values
                return np.asarray(values)

            if name in self.dataset.variables:
                values = self.dataset[name].values
                return np.asarray(values)

        return None

    def _nearest_selection(
        self,
        *,
        latitude: float,
        longitude: float,
        depth: float,
        time: datetime | np.datetime64,
        variable: str,
    ) -> xr.DataArray:
        data = self.dataset[variable]

        selection: dict[str, object] = {}

        latitude_name = self._coordinate_name(("latitude", "lat"))
        longitude_name = self._coordinate_name(("longitude", "lon"))
        depth_name = self._coordinate_name(("depth", "depth_m", "lev", "level", "z"))

        if latitude_name is not None:
            selection[latitude_name] = latitude

        if longitude_name is not None:
            selection[longitude_name] = longitude

        if depth_name is not None and depth_name in data.dims:
            selection[depth_name] = depth

        if "time" in data.dims:
            selection["time"] = self._to_datetime64(time)

        return data.sel(selection, method="nearest")

    def _coordinate_name(
        self,
        names: tuple[str, ...],
    ) -> str | None:
        for name in names:
            if name in self.dataset.coords:
                return name

            if name in self.dataset.variables:
                return name

        return None

    @staticmethod
    def _to_datetime64(
        value: datetime | np.datetime64,
    ) -> np.datetime64:
        if isinstance(value, np.datetime64):
            if np.isnat(value):
                raise ValueError("Datetime value cannot be NaT.")
            return value.astype("datetime64[ns]")

        if isinstance(value, datetime):
            return np.datetime64(value, "ns")

        raise TypeError(
            f"Unsupported datetime type: {type(value).__name__}"
        )