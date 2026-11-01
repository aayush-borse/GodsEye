"""AI command API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ocean_backend.ai.executor import (
    OceanCommandExecutor,
)
from ocean_backend.ai.parser import (
    OceanCommandParser,
)


router = APIRouter(
    prefix="/ai",
    tags=["ai"],
)


parser = OceanCommandParser()
executor = OceanCommandExecutor()


class AICommandRequest(BaseModel):
    """Natural-language command request."""

    text: str
    dataset_id: str | None = None
    observation_id: str | None = None


class AICommandResponse(BaseModel):
    """Structured response from the AI command layer."""

    command: dict
    result: dict


@router.post(
    "/command",
    response_model=AICommandResponse,
)
def execute_ai_command(
    request: AICommandRequest,
):
    """
    Parse and validate a natural-language ocean command.

    No LLM is required for this MVP endpoint.
    """

    try:

        command = parser.parse(
            text=request.text,
            dataset_id=request.dataset_id,
            observation_id=request.observation_id,
        )

        result = executor.execute(
            command
        )

        return {
            "command": command.model_dump(
                mode="json"
            ),
            "result": result,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc