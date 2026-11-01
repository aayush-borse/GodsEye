from dataclasses import dataclass
from datetime import datetime


@dataclass
class Observation:
    """
    A single in-situ ocean observation.
    """

    platform_id: str
    latitude: float
    longitude: float
    depth: float
    time: datetime
    variable: str
    value: float
    quality_flag: str

    cycle_number: int | None = None
    value_source: str | None = None
    data_mode: str | None = None