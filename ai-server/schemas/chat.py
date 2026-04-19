"""Chat API request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message for the agent.")


class ChatResponse(BaseModel):
    type: Literal["text", "tool"]
    content: str
    file: str | None = None
