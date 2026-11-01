"""Validation rules for AI-generated ocean commands."""

from __future__ import annotations

from ocean_backend.ai.commands import CommandType, OceanCommand


class CommandValidationError(ValueError):
    """Raised when an AI command is incomplete or invalid."""


SUPPORTED_VARIABLES = {
    "temperature",
    "salinity",
    "u",
    "v",
    "thetao",
    "so",
    "uo",
    "vo",
}


def validate_command(
    command: OceanCommand,
) -> OceanCommand:
    """
    Validate an AI command before it reaches the scientific backend.

    This is intentionally deterministic. The AI is never trusted to
    decide whether a scientific operation is valid.
    """

    if command.command in {
        CommandType.SHOW_VOLUME,
        CommandType.SHOW_DIFFERENCE,
        CommandType.SHOW_THERMOCLINE,
        CommandType.FILTER_BY_DEPTH,
        CommandType.FILTER_BY_TIME,
        CommandType.FILTER_BY_VARIABLE,
        CommandType.FILTER_BY_CONFIDENCE,
    }:
        if not command.dataset_id:
            raise CommandValidationError(
                f"{command.command.value} requires dataset_id."
            )

    if command.variable is not None:

        variable = command.variable.strip().lower()

        if variable not in SUPPORTED_VARIABLES:
            raise CommandValidationError(
                f"Unsupported variable '{command.variable}'."
            )

    if command.command == CommandType.SHOW_PROFILE:

        if not command.observation_id:
            raise CommandValidationError(
                "SHOW_PROFILE requires observation_id."
            )

    if command.command == CommandType.SELECT_OBSERVATION:

        if (
            command.observation_id is None
            and (
                command.latitude is None
                or command.longitude is None
            )
        ):
            raise CommandValidationError(
                "SELECT_OBSERVATION requires either observation_id "
                "or latitude and longitude."
            )

    if command.command == CommandType.COMPARE_MODEL_OBSERVATION:

        if not command.dataset_id:
            raise CommandValidationError(
                "COMPARE_MODEL_OBSERVATION requires dataset_id."
            )

        if not command.observation_id:
            raise CommandValidationError(
                "COMPARE_MODEL_OBSERVATION requires observation_id."
            )

        if not command.variable:
            raise CommandValidationError(
                "COMPARE_MODEL_OBSERVATION requires variable."
            )

    if command.command == CommandType.FILTER_BY_DEPTH:

        if (
            command.depth_min is None
            and command.depth_max is None
            and command.depth is None
        ):
            raise CommandValidationError(
                "FILTER_BY_DEPTH requires a depth value or depth range."
            )

        if (
            command.depth_min is not None
            and command.depth_max is not None
            and command.depth_min > command.depth_max
        ):
            raise CommandValidationError(
                "depth_min cannot be greater than depth_max."
            )

    if command.command == CommandType.FILTER_BY_TIME:

        if command.time_index is None:
            raise CommandValidationError(
                "FILTER_BY_TIME requires time_index."
            )

    if command.command == CommandType.FILTER_BY_VARIABLE:

        if not command.variable:
            raise CommandValidationError(
                "FILTER_BY_VARIABLE requires variable."
            )

    if command.command == CommandType.FILTER_BY_CONFIDENCE:

        if not command.confidence:
            raise CommandValidationError(
                "FILTER_BY_CONFIDENCE requires confidence."
            )

        allowed_confidence = {
            "HIGH",
            "MEDIUM",
            "LOW",
        }

        if command.confidence.upper() not in allowed_confidence:
            raise CommandValidationError(
                "confidence must be HIGH, MEDIUM or LOW."
            )

    return command