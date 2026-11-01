"""Structured schemas used by the ANVIKSHA AI command layer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ocean_backend.ai.commands import AICommandType


Variable = Literal[
    "temperature",
    "salinity",
    "u",
    "v",
    "chlorophyll",
]


class Location(BaseModel):
    """Geographic location."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(
        ge=-90.0,
        le=90.0,
        description="Latitude in degrees.",
    )

    longitude: float = Field(
        ge=-180.0,
        le=180.0,
        description="Longitude in degrees.",
    )


class DepthRange(BaseModel):
    """Depth interval in metres."""

    model_config = ConfigDict(extra="forbid")

    minimum_m: float = Field(
        ge=0.0,
        description="Minimum depth in metres.",
    )

    maximum_m: float = Field(
        ge=0.0,
        description="Maximum depth in metres.",
    )


class AICommand(BaseModel):
    """
    Validated command produced by the AI intent layer.

    This is the boundary between natural language and the
    deterministic scientific/visualization system.
    """

    model_config = ConfigDict(extra="forbid")

    command: AICommandType

    variable: Variable | None = None

    location: Location | None = None

    depth_m: float | None = Field(
        default=None,
        ge=0.0,
    )

    depth_range: DepthRange | None = None

    time: datetime | None = None

    observation_id: str | None = None

    confidence_threshold: Literal[
        "HIGH",
        "MEDIUM",
        "LOW",
        "ANY",
    ] | None = None