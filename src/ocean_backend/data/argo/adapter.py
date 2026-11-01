"""Argo GDAC NetCDF ingestion."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import xarray as xr

from ocean_backend.data.observations import Observation


@dataclass
class ArgoMeasurement:
    """One measurement from an Argo profile."""

    pressure: float
    depth: float
    value: float
    quality_flag: str
    value_source: str


@dataclass
class ArgoProfile:
    """A single Argo vertical profile."""

    observation_id: str
    platform_id: str
    cycle_number: int
    latitude: float
    longitude: float
    time: datetime
    data_mode: str
    temperature: list[ArgoMeasurement]
    salinity: list[ArgoMeasurement]


def decode_string(value) -> str:
    """Convert NetCDF byte/string values into a normal Python string."""

    if isinstance(value, bytes):
        return value.decode("utf-8").strip()

    return str(value).strip()


def argo_qc_to_internal(qc_value) -> str:
    """Convert an Argo measurement QC flag to our internal representation."""

    if qc_value is None:
        return "UNKNOWN"

    if isinstance(qc_value, bytes):
        qc_value = qc_value.decode("utf-8")

    qc = str(qc_value).strip()

    if not qc or qc.lower() == "nan":
        return "UNKNOWN"

    if qc in {"1", "2"}:
        return "PASS"

    if qc == "3":
        return "SUSPECT"

    if qc == "4":
        return "FAIL"

    return "UNKNOWN"


def _valid_number(value) -> bool:
    """Return True when a value is finite."""

    try:
        return bool(np.isfinite(value))
    except (TypeError, ValueError):
        return False


def _numpy_datetime_to_datetime(value) -> datetime:
    """Convert NumPy datetime64 to a Python datetime."""

    return value.astype("datetime64[us]").astype(datetime)


def _pressure_to_depth(
    pressure_dbar: float,
    latitude: float,
) -> float:
    """
    Convert Argo pressure in decibar to approximate depth in metres.

    Uses the UNESCO 1983 pressure-to-depth relationship with
    latitude-dependent gravitational acceleration.
    """

    pressure = float(pressure_dbar)

    if not np.isfinite(pressure):
        raise ValueError("Argo pressure must be finite.")

    if pressure < 0:
        raise ValueError("Argo pressure cannot be negative.")

    latitude_radians = np.deg2rad(latitude)

    sin_lat_squared = np.sin(latitude_radians) ** 2

    gravity = 9.780318 * (
        1.0
        + 5.2788e-3 * sin_lat_squared
        + 2.36e-5 * sin_lat_squared**2
    )

    depth = (
        (
            (
                -1.82e-15 * pressure
                + 2.279e-10
            )
            * pressure
            - 2.2512e-5
        )
        * pressure
        + 9.72659
    ) * pressure

    depth /= gravity + 5.84e-6 * pressure

    return float(depth)


def _select_measurement(
    raw_value,
    adjusted_value,
    raw_qc,
    adjusted_qc,
) -> tuple[float | None, str, str]:
    """
    Select the best available measurement.

    Prefer adjusted data when the adjusted value has usable QC.
    Otherwise fall back to the raw measurement.
    """

    if _valid_number(adjusted_value):
        adjusted_quality = argo_qc_to_internal(
            adjusted_qc
        )

        if adjusted_quality in {"PASS", "SUSPECT"}:
            return (
                float(adjusted_value),
                adjusted_quality,
                "ADJUSTED",
            )

    if _valid_number(raw_value):
        raw_quality = argo_qc_to_internal(
            raw_qc
        )

        if raw_quality != "UNKNOWN":
            return (
                float(raw_value),
                raw_quality,
                "RAW",
            )

    return None, "UNKNOWN", "NONE"


class ArgoAdapter:
    """Read Argo GDAC profile NetCDF files."""

    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path

    def open(self) -> xr.Dataset:
        """Open an Argo NetCDF dataset with a portable engine fallback.

        NetCDF4 is the preferred engine for real GDAC files. The bundled
        small demo fixture is classic NetCDF and can also be opened by
        SciPy, which keeps lightweight development environments usable.
        """
        try:
            return xr.open_dataset(self.dataset_path, engine="netcdf4")
        except ImportError:
            return xr.open_dataset(self.dataset_path, engine="scipy")

    def load_profiles(self) -> list[ArgoProfile]:
        """Load all profiles from the Argo NetCDF file."""

        with self.open() as dataset:
            return [
                self._load_profile(
                    dataset,
                    profile_index,
                )
                for profile_index in range(
                    dataset.sizes["N_PROF"]
                )
            ]

    def _load_profile(
        self,
        dataset: xr.Dataset,
        profile_index: int,
    ) -> ArgoProfile:

        platform_id = decode_string(
            dataset["PLATFORM_NUMBER"].values[
                profile_index
            ]
        )

        cycle_number = int(
            dataset["CYCLE_NUMBER"].values[
                profile_index
            ]
        )

        latitude = float(
            dataset["LATITUDE"].values[
                profile_index
            ]
        )

        longitude = float(
            dataset["LONGITUDE"].values[
                profile_index
            ]
        )

        time = _numpy_datetime_to_datetime(
            dataset["JULD"].values[
                profile_index
            ]
        )

        observation_id = (
            f"{platform_id}_{cycle_number}"
        )

        data_mode = decode_string(
            dataset["DATA_MODE"].values[
                profile_index
            ]
        )

        pressure = dataset["PRES"].values[
            profile_index
        ]

        temperature = dataset["TEMP"].values[
            profile_index
        ]

        temperature_adjusted = dataset[
            "TEMP_ADJUSTED"
        ].values[profile_index]

        temperature_qc = dataset[
            "TEMP_QC"
        ].values[profile_index]

        temperature_adjusted_qc = dataset[
            "TEMP_ADJUSTED_QC"
        ].values[profile_index]

        salinity = dataset["PSAL"].values[
            profile_index
        ]

        salinity_adjusted = dataset[
            "PSAL_ADJUSTED"
        ].values[profile_index]

        salinity_qc = dataset[
            "PSAL_QC"
        ].values[profile_index]

        salinity_adjusted_qc = dataset[
            "PSAL_ADJUSTED_QC"
        ].values[profile_index]

        temperature_measurements: list[
            ArgoMeasurement
        ] = []

        salinity_measurements: list[
            ArgoMeasurement
        ] = []

        for level in range(len(pressure)):

            pressure_dbar = float(
                pressure[level]
            )

            # Ignore NaN, fill-value, sentinel,
            # and physically impossible pressures.
            if (
                not np.isfinite(pressure_dbar)
                or pressure_dbar < 0
            ):
                continue

            depth_m = _pressure_to_depth(
                pressure_dbar,
                latitude,
            )

            temp, temp_qc, temp_source = (
                _select_measurement(
                    temperature[level],
                    temperature_adjusted[level],
                    temperature_qc[level],
                    temperature_adjusted_qc[level],
                )
            )

            if temp is not None:
                temperature_measurements.append(
                    ArgoMeasurement(
                        pressure=pressure_dbar,
                        depth=depth_m,
                        value=temp,
                        quality_flag=temp_qc,
                        value_source=temp_source,
                    )
                )

            sal, sal_qc, sal_source = (
                _select_measurement(
                    salinity[level],
                    salinity_adjusted[level],
                    salinity_qc[level],
                    salinity_adjusted_qc[level],
                )
            )

            if sal is not None:
                salinity_measurements.append(
                    ArgoMeasurement(
                        pressure=pressure_dbar,
                        depth=depth_m,
                        value=sal,
                        quality_flag=sal_qc,
                        value_source=sal_source,
                    )
                )

        return ArgoProfile(
            observation_id=observation_id,
            platform_id=platform_id,
            cycle_number=cycle_number,
            latitude=latitude,
            longitude=longitude,
            time=time,
            data_mode=data_mode,
            temperature=temperature_measurements,
            salinity=salinity_measurements,
        )

    def load_observations(
        self,
    ) -> list[Observation]:
        """Flatten Argo profiles into individual observations."""

        observations: list[Observation] = []

        for profile in self.load_profiles():

            for measurement in profile.temperature:

                observations.append(
                    Observation(
                        platform_id=profile.observation_id,
                        latitude=profile.latitude,
                        longitude=profile.longitude,
                        depth=measurement.depth,
                        time=profile.time,
                        variable="thetao",
                        value=measurement.value,
                        quality_flag=measurement.quality_flag,
                        cycle_number=profile.cycle_number,
                        value_source=measurement.value_source,
                        data_mode=profile.data_mode,
                    )
                )

            for measurement in profile.salinity:

                observations.append(
                    Observation(
                        platform_id=profile.observation_id,
                        latitude=profile.latitude,
                        longitude=profile.longitude,
                        depth=measurement.depth,
                        time=profile.time,
                        variable="so",
                        value=measurement.value,
                        quality_flag=measurement.quality_flag,
                        cycle_number=profile.cycle_number,
                        value_source=measurement.value_source,
                        data_mode=profile.data_mode,
                    )
                )

        return observations