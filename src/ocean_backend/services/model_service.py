"""Application service for model-observation comparisons."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr

from ocean_backend.data.observation_store import ObservationStore
from ocean_backend.data.observations import Observation
from ocean_backend.models.schemas import (
    ComparisonEvidence,
    ComparisonRequest,
)
from ocean_backend.science.collocation import build_collocation_result
from ocean_backend.science.comparison_validity import ComparisonValidityGate
from ocean_backend.science.interpolation import interpolate_4d
from ocean_backend.science.model_support import ModelSupportValidator


class ModelService:
    """Coordinates model data, observations, validation and comparison."""

    MODEL_VARIABLES = {
        "temperature": "thetao",
        "salinity": "so",
        "u": "uo",
        "v": "vo",
        "eastward_velocity": "uo",
        "northward_velocity": "vo",
    }

    OBSERVATION_VARIABLES = {
        "temperature": {
            "temperature",
            "thetao",
        },
        "salinity": {
            "salinity",
            "so",
        },
        "u": {
            "u",
            "uo",
        },
        "v": {
            "v",
            "vo",
        },
        "eastward_velocity": {
            "u",
            "uo",
            "eastward_velocity",
        },
        "northward_velocity": {
            "v",
            "vo",
            "northward_velocity",
        },
    }

    def __init__(
        self,
        dataset: xr.Dataset | str | Path,
        observation_store: ObservationStore | None = None,
    ) -> None:
        """Create the model comparison service."""

        if isinstance(dataset, (str, Path)):
            self.dataset = xr.open_dataset(dataset)
        elif isinstance(dataset, xr.Dataset):
            self.dataset = dataset
        else:
            raise TypeError(
                "dataset must be an xarray.Dataset or a path to a NetCDF file."
            )

        self.observation_store = (
            observation_store
            if observation_store is not None
            else ObservationStore()
        )

        self.model_support_validator = ModelSupportValidator(
            self.dataset
        )

        self.validity_gate = ComparisonValidityGate(
            model_support_validator=self.model_support_validator,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(
        self,
        request: ComparisonRequest,
    ) -> ComparisonEvidence:
        """
        Compare model output against an observation.

        When an observation is selected, the model is collocated at the
        observation's actual latitude, longitude, depth and timestamp.

        The request coordinates are retained as the user's requested
        comparison context.
        """

        model_variable = self._validate_variable(
            request.variable
        )

        observation: Observation | None = None

        # --------------------------------------------------------------
        # Resolve observation first.
        # --------------------------------------------------------------
        if request.observation_id is not None:
            observation = self._resolve_observation(
                observation_id=request.observation_id,
                variable=request.variable,
                depth=request.depth_m,
            )

            self._validate_observation_variable(
                observation=observation,
                requested_variable=request.variable,
            )

        # --------------------------------------------------------------
        # Determine the coordinates that the model must support.
        #
        # If an observation is selected, the actual observation
        # coordinates are authoritative for collocation.
        # --------------------------------------------------------------
        comparison_latitude = (
            observation.latitude
            if observation is not None
            else request.latitude
        )

        comparison_longitude = (
            observation.longitude
            if observation is not None
            else request.longitude
        )

        comparison_depth = (
            observation.depth
            if observation is not None
            else request.depth_m
        )

        comparison_time = (
            observation.time
            if observation is not None
            else request.time
        )

        model_support = self.validity_gate.validate_model_request(
            latitude=comparison_latitude,
            longitude=comparison_longitude,
            depth=comparison_depth,
            time=comparison_time,
            variable=model_variable,
        )

        if not model_support.supported:
            raise ValueError(
                "Model does not support the requested comparison: "
                + "; ".join(model_support.reasons)
            )

        # --------------------------------------------------------------
        # MODEL-ONLY REQUEST
        # --------------------------------------------------------------
        if observation is None:
            model_value = self._interpolate_model(
                variable=model_variable,
                latitude=request.latitude,
                longitude=request.longitude,
                depth=request.depth_m,
                time=request.time,
            )

            return ComparisonEvidence(
                variable=request.variable,
                requested=request,
                model_value=model_value,
                observed_value=None,
                difference=None,
                spatial_distance_km=None,
                temporal_difference_hours=None,
                depth_difference_m=None,
                observation_qc="UNKNOWN",
                interpolation="trilinear + linear temporal",
                confidence="UNAVAILABLE",
                confidence_reasons=[
                    "No observation was selected for comparison."
                ],
            )

        # --------------------------------------------------------------
        # SCIENTIFIC VALIDITY
        # --------------------------------------------------------------
        comparison_validity = self.validity_gate.validate(
            observation=observation,
            variable=model_variable,
        )

        if not comparison_validity.valid:
            raise ValueError(
                "Comparison is scientifically invalid: "
                + "; ".join(comparison_validity.reasons)
            )

        # --------------------------------------------------------------
        # MODEL COLLOCATION
        #
        # Evaluate the model at the actual observation coordinates.
        # --------------------------------------------------------------
        model_value = self._interpolate_model(
            variable=model_variable,
            latitude=observation.latitude,
            longitude=observation.longitude,
            depth=observation.depth,
            time=observation.time,
        )

        # --------------------------------------------------------------
        # Find nearest horizontal model grid point.
        #
        # This is used only to describe spatial separation from the
        # observation to the model grid.
        # --------------------------------------------------------------
        model_latitude = self._nearest_coordinate(
            names=("latitude", "lat"),
            value=observation.latitude,
        )

        model_longitude = self._nearest_coordinate(
            names=("longitude", "lon"),
            value=observation.longitude,
        )

        # --------------------------------------------------------------
        # Depth difference semantics
        #
        # This field represents:
        #
        #     |observation depth - requested depth|
        #
        # It does NOT represent the distance between the observation
        # depth and the nearest model vertical level.
        # --------------------------------------------------------------
        evidence_depth_difference = abs(
            float(observation.depth)
            - float(request.depth_m)
        )

        # --------------------------------------------------------------
        # Temporal difference semantics
        #
        # Because the model is explicitly collocated at the observation
        # timestamp, the temporal separation of the actual collocation
        # is zero.
        #
        # The user's requested time may differ, but that is not the
        # model-observation temporal separation represented by this
        # evidence field.
        # --------------------------------------------------------------
        evidence_time_difference = 0.0

        # --------------------------------------------------------------
        # Build scientific collocation result.
        # --------------------------------------------------------------
        collocation = build_collocation_result(
            observation=observation,
            model_value=model_value,
            model_latitude=model_latitude,
            model_longitude=model_longitude,
            model_depth=request.depth_m,
            model_time=request.time,
            interpolation_method="trilinear + linear temporal",
        )

        # --------------------------------------------------------------
        # Build API evidence explicitly.
        # --------------------------------------------------------------
        return ComparisonEvidence(
            variable=request.variable,
            requested=request,
            model_value=collocation.model_value,
            observed_value=collocation.observed_value,
            difference=collocation.difference,
            spatial_distance_km=collocation.distance_km,
            temporal_difference_hours=evidence_time_difference,
            depth_difference_m=evidence_depth_difference,
            observation_qc=collocation.quality_flag,
            interpolation=collocation.interpolation_method,
            confidence=collocation.confidence,
            confidence_reasons=collocation.confidence_reasons,
        )

    # ------------------------------------------------------------------
    # Variable handling
    # ------------------------------------------------------------------

    def _validate_variable(
        self,
        variable: str,
    ) -> str:
        """Validate the requested variable and return its model name."""

        if not variable or not str(variable).strip():
            raise ValueError(
                "Comparison variable cannot be empty."
            )

        normalized = str(variable).strip().lower()

        if normalized not in self.MODEL_VARIABLES:
            supported = ", ".join(
                sorted(self.MODEL_VARIABLES)
            )

            raise ValueError(
                f"Unsupported comparison variable "
                f"'{variable}'. "
                f"Supported variables: {supported}."
            )

        model_variable = self.MODEL_VARIABLES[
            normalized
        ]

        if model_variable not in self.dataset.data_vars:
            raise ValueError(
                f"Model variable '{model_variable}' "
                f"is not available in the loaded dataset."
            )

        return model_variable

    # ------------------------------------------------------------------
    # Observation handling
    # ------------------------------------------------------------------

    def _resolve_observation(
        self,
        *,
        observation_id: str,
        variable: str,
        depth: float,
    ) -> Observation:
        """Resolve an observation from the observation store."""

        if not observation_id or not observation_id.strip():
            raise ValueError(
                "Observation ID cannot be empty."
            )

        # First try a direct ID lookup if the store provides one.
        observation = self._get_observation_by_id(
            observation_id
        )

        if observation is not None:
            return observation

        if not hasattr(
            self.observation_store,
            "get_by_profile",
        ):
            raise ValueError(
                f"Observation not found for selector "
                f"'{observation_id}'."
            )

        observation_variables = (
            self.OBSERVATION_VARIABLES.get(
                variable,
                set(),
            )
        )

        for observation_variable in observation_variables:
            try:
                profile = (
                    self.observation_store.get_by_profile(
                        observation_id,
                        observation_variable,
                        depth,
                    )
                )
            except (
                KeyError,
                ValueError,
                IndexError,
            ):
                continue

            observation = (
                self._extract_observation_from_profile(
                    profile=profile,
                    observation_id=observation_id,
                )
            )

            if observation is not None:
                return observation

        raise ValueError(
            f"Observation not found for selector "
            f"'{observation_id}'."
        )

    def _get_observation_by_id(
        self,
        observation_id: str,
    ) -> Observation | None:
        """Try direct observation lookup methods."""

        if hasattr(
            self.observation_store,
            "get",
        ):
            try:
                result = self.observation_store.get(
                    observation_id
                )

                if isinstance(
                    result,
                    Observation,
                ):
                    return result

            except (
                KeyError,
                ValueError,
            ):
                pass

        if hasattr(
            self.observation_store,
            "get_by_id",
        ):
            try:
                result = (
                    self.observation_store.get_by_id(
                        observation_id
                    )
                )

                if isinstance(
                    result,
                    Observation,
                ):
                    return result

            except (
                KeyError,
                ValueError,
            ):
                pass

        return None

    @staticmethod
    def _extract_observation_from_profile(
        *,
        profile,
        observation_id: str,
    ) -> Observation | None:
        """Extract an Observation from a profile lookup result."""

        if isinstance(
            profile,
            Observation,
        ):
            return profile

        if profile is None:
            return None

        if isinstance(
            profile,
            (list, tuple),
        ):
            for item in profile:
                if isinstance(
                    item,
                    Observation,
                ):
                    return item

            return None

        if isinstance(
            profile,
            dict,
        ):
            candidate = profile.get(
                observation_id
            )

            if isinstance(
                candidate,
                Observation,
            ):
                return candidate

            for candidate in profile.values():
                if isinstance(
                    candidate,
                    Observation,
                ):
                    return candidate

        return None

    def _validate_observation_variable(
        self,
        *,
        observation: Observation,
        requested_variable: str,
    ) -> None:
        """Ensure the selected observation matches the requested variable."""

        expected_variables = (
            self.OBSERVATION_VARIABLES.get(
                requested_variable
            )
        )

        if expected_variables is None:
            raise ValueError(
                f"No observation adapter is configured "
                f"for variable '{requested_variable}'."
            )

        actual = str(
            observation.variable
        ).strip().lower()

        if actual not in expected_variables:
            raise ValueError(
                f"Observation variable "
                f"'{observation.variable}' "
                f"does not match requested variable "
                f"'{requested_variable}'."
            )

    # ------------------------------------------------------------------
    # Model interpolation
    # ------------------------------------------------------------------

    def _interpolate_model(
        self,
        *,
        variable: str,
        latitude: float,
        longitude: float,
        depth: float,
        time: datetime,
    ) -> float:
        """Interpolate a model variable at a 4D point."""

        data = self.dataset[variable]

        try:
            value = interpolate_4d(
                data,
                latitude=latitude,
                longitude=longitude,
                depth=depth,
                time=time,
            )
        except TypeError:
            # Compatibility with implementations that accept positional
            # arguments instead of keyword arguments.
            value = interpolate_4d(
                data,
                latitude,
                longitude,
                depth,
                time,
            )

        value = self._scalarize(
            value
        )

        if not np.isfinite(value):
            raise ValueError(
                "Model interpolation returned an invalid "
                "value (NaN or infinite)."
            )

        return value

    @staticmethod
    def _scalarize(
        value,
    ) -> float:
        """Convert scalar-like values to a Python float."""

        if isinstance(
            value,
            xr.DataArray,
        ):
            if value.size != 1:
                raise ValueError(
                    "Model interpolation returned "
                    "more than one value."
                )

            value = value.values

        array = np.asarray(
            value
        )

        if array.size != 1:
            raise ValueError(
                "Model interpolation returned "
                "more than one value."
            )

        return float(
            array.reshape(-1)[0]
        )

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _nearest_coordinate(
        self,
        *,
        names: tuple[str, ...],
        value: float,
    ) -> float:
        """Return the nearest finite model coordinate."""

        coordinate = self._find_coordinate(
            names
        )

        if coordinate is None:
            raise ValueError(
                f"Model dataset does not contain "
                f"a coordinate matching {names}."
            )

        values = np.asarray(
            coordinate.values,
            dtype=float,
        ).reshape(-1)

        if values.size == 0:
            raise ValueError(
                f"Model coordinate "
                f"{coordinate.name!r} contains no values."
            )

        finite_values = values[
            np.isfinite(values)
        ]

        if finite_values.size == 0:
            raise ValueError(
                f"Model coordinate "
                f"{coordinate.name!r} contains no "
                f"finite values."
            )

        index = int(
            np.argmin(
                np.abs(
                    finite_values
                    - float(value)
                )
            )
        )

        return float(
            finite_values[index]
        )

    def _nearest_time(
        self,
        value,
    ) -> np.datetime64:
        """Return the nearest model output time."""

        coordinate = self._find_coordinate(
            ("time",)
        )

        if coordinate is None:
            raise ValueError(
                "Model dataset does not contain "
                "a time coordinate."
            )

        values = np.asarray(
            coordinate.values,
            dtype="datetime64[ns]",
        ).reshape(-1)

        valid_values = values[
            ~np.isnat(values)
        ]

        if valid_values.size == 0:
            raise ValueError(
                "Model dataset contains no "
                "valid time values."
            )

        requested = self._to_datetime64(
            value
        )

        differences = np.abs(
            valid_values.astype("int64")
            - requested.astype("int64")
        )

        index = int(
            np.argmin(differences)
        )

        return valid_values[index]

    def _find_coordinate(
        self,
        names: tuple[str, ...],
    ) -> xr.DataArray | None:
        """Find the first matching coordinate."""

        for name in names:
            if name in self.dataset.coords:
                return self.dataset.coords[name]

            if name in self.dataset.variables:
                return self.dataset[name]

        return None

    @staticmethod
    def _to_datetime64(
        value,
    ) -> np.datetime64:
        """Normalize datetime-like values."""

        if isinstance(
            value,
            np.datetime64,
        ):
            if np.isnat(value):
                raise ValueError(
                    "Datetime value cannot be NaT."
                )

            return value.astype(
                "datetime64[ns]"
            )

        if isinstance(
            value,
            datetime,
        ):
            return np.datetime64(
                value,
                "ns",
            )

        raise TypeError(
            f"Unsupported datetime type: "
            f"{type(value).__name__}"
        )