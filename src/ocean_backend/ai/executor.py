"""Execution layer for validated ocean intelligence commands."""

from __future__ import annotations

from typing import Any

from ocean_backend.ai.commands import (
    CommandType,
    OceanCommand,
)
from ocean_backend.ai.validator import (
    validate_command,
)
from ocean_backend.services.dataset_runtime import (
    dataset_registry,
)
from ocean_backend.services.model_service import (
    ModelService,
)


class OceanCommandExecutor:
    """
    Execute validated commands against existing backend services.

    The executor does not perform scientific calculations itself.

    It only routes commands to the appropriate scientific service.
    """

    def execute(
        self,
        command: OceanCommand,
    ) -> dict[str, Any]:

        # ------------------------------------------------------
        # Validate before execution
        # ------------------------------------------------------

        command = validate_command(
            command
        )

        # ------------------------------------------------------
        # Visualization commands
        # ------------------------------------------------------

        if command.command == CommandType.SHOW_VOLUME:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "show_volume",
                "dataset_id": command.dataset_id,
                "variable": command.variable,
            }

        if command.command == CommandType.SHOW_PROFILE:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "show_profile",
                "observation_id": (
                    command.observation_id
                ),
            }

        if command.command == CommandType.SHOW_OBSERVATIONS:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "show_observations",
            }

        if command.command == CommandType.SHOW_DIFFERENCE:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "show_difference",
                "dataset_id": command.dataset_id,
                "variable": command.variable,
            }

        if command.command == CommandType.SHOW_THERMOCLINE:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "show_thermocline",
                "dataset_id": command.dataset_id,
            }

        # ------------------------------------------------------
        # Filtering commands
        # ------------------------------------------------------

        if command.command == CommandType.FILTER_BY_DEPTH:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "filter_depth",
                "dataset_id": command.dataset_id,
                "depth": command.depth,
                "depth_min": command.depth_min,
                "depth_max": command.depth_max,
            }

        if command.command == CommandType.FILTER_BY_TIME:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "filter_time",
                "dataset_id": command.dataset_id,
                "time_index": command.time_index,
            }

        if command.command == CommandType.FILTER_BY_VARIABLE:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "filter_variable",
                "dataset_id": command.dataset_id,
                "variable": command.variable,
            }

        if command.command == CommandType.FILTER_BY_CONFIDENCE:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "filter_confidence",
                "dataset_id": command.dataset_id,
                "confidence": command.confidence,
            }

        # ------------------------------------------------------
        # Observation selection
        # ------------------------------------------------------

        if command.command == CommandType.SELECT_OBSERVATION:

            return {
                "command": command.command.value,
                "status": "ready",
                "action": "select_observation",
                "observation_id": (
                    command.observation_id
                ),
                "latitude": command.latitude,
                "longitude": command.longitude,
                "depth": command.depth,
            }

        # ------------------------------------------------------
        # Model / observation comparison
        # ------------------------------------------------------

        if command.command == CommandType.COMPARE_MODEL_OBSERVATION:

            return self._compare_model_observation(
                command
            )

        raise ValueError(
            f"Unsupported command: "
            f"{command.command.value}"
        )

    # ----------------------------------------------------------
    # Scientific execution
    # ----------------------------------------------------------

    def _compare_model_observation(
        self,
        command: OceanCommand,
    ) -> dict[str, Any]:
        dataset = dataset_registry.get(command.dataset_id)
        if dataset is None:
            raise ValueError(
                f"Dataset '{command.dataset_id}' was not found."
            )

        # The API comparison route owns the bundled observation store.
        # Import lazily here so the AI module remains lightweight and avoids
        # circular imports during application startup.
        from ocean_backend.api.routes.comparison import observation_store

        model_service = ModelService(
            dataset,
            observation_store=observation_store,
        )

        observation = observation_store.get_by_id(command.observation_id or "")
        if observation is None:
            raise ValueError(
                f"Observation '{command.observation_id}' was not found."
            )

        variable = command.variable or "temperature"
        from ocean_backend.models.schemas import ComparisonRequest

        evidence = model_service.compare(
            ComparisonRequest(
                latitude=observation.latitude,
                longitude=observation.longitude,
                depth_m=observation.depth,
                time=observation.time,
                variable=variable,
                observation_id=command.observation_id,
            )
        )

        return evidence.model_dump(mode="json")
