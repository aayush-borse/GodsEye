"""Validated commands understood by the ocean intelligence layer."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CommandType(str, Enum):
    """Actions that the AI visualization layer is allowed to request."""

    SHOW_VOLUME = "SHOW_VOLUME"
    SHOW_PROFILE = "SHOW_PROFILE"
    SHOW_OBSERVATIONS = "SHOW_OBSERVATIONS"
    SHOW_DIFFERENCE = "SHOW_DIFFERENCE"
    SHOW_THERMOCLINE = "SHOW_THERMOCLINE"

    FILTER_BY_DEPTH = "FILTER_BY_DEPTH"
    FILTER_BY_TIME = "FILTER_BY_TIME"
    FILTER_BY_VARIABLE = "FILTER_BY_VARIABLE"
    FILTER_BY_CONFIDENCE = "FILTER_BY_CONFIDENCE"

    SELECT_OBSERVATION = "SELECT_OBSERVATION"
    COMPARE_MODEL_OBSERVATION = "COMPARE_MODEL_OBSERVATION"


class OceanCommand(BaseModel):
    """
    Structured command produced by the AI intent layer.

    The AI does not directly execute Python, SQL, xarray operations,
    interpolation or scientific calculations. It only produces one
    of these validated commands.
    """

    command: CommandType

    dataset_id: str | None = None
    variable: str | None = None

    observation_id: str | None = None

    latitude: float | None = None
    longitude: float | None = None
    depth: float | None = None

    depth_min: float | None = None
    depth_max: float | None = None

    time_index: int | None = Field(
        default=None,
        ge=0,
    )

    confidence: str | None = None

    limit: int | None = Field(
        default=None,
        ge=1,
        le=5000,
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict,
    )
# Backwards-compatible name used by the earlier public AI schema.
AICommandType = CommandType
