"""Tool invocation schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """Declarative tool metadata used for prompts + validation."""

    name: str
    description: str
    args_schema: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    status: Literal["success", "error"]
    file: str | None = None
    error: str | None = None
    # Structured payloads for non-file tools (e.g. web search summaries).
    details: dict[str, Any] | None = None
