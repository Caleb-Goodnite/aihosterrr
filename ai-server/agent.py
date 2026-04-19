"""Agent orchestration: prompt shaping, JSON parsing, tool routing.

This module is intentionally structured for future multi-step loops:
- ``Agent.chat`` performs a single model+tool hop today.
- ``Agent.chat_loop`` can later iterate until a terminal ``text`` response.
"""

from __future__ import annotations

import json
from typing import Any

from llm import OllamaClient, OllamaError
from schemas.chat import ChatResponse
from schemas.tool import ToolExecutionResult
from tools.registry import ToolRegistry, get_default_registry, tools_prompt_json_schema
from utils.json_parser import parse_model_json
from utils.logger import get_logger

logger = get_logger(__name__)


def _system_prompt() -> str:
    tools = tools_prompt_json_schema()
    return f"""You are a backend agent that MUST respond with a single JSON object ONLY (no markdown, no prose).

Valid shapes:

1) Normal answer:
{{"type":"text","content":"<string>"}}

2) Tool call:
{{"type":"tool","tool":"<tool_name>","args":{{...}}}}

Tool catalog:
{tools}

Rules:
- Output MUST be valid JSON.
- If you are not calling a tool, use type \"text\".
- If you call a tool, use type \"tool\" with correct tool name and args matching the schema.
- Never include extra keys beyond those required for the chosen shape.
- Never output shell commands or attempt to access paths outside the provided tool args semantics.
"""


def _validate_model_payload(obj: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None

    obj_type = obj.get("type")
    if obj_type == "text":
        if not isinstance(obj.get("content"), str):
            return None
        return obj

    if obj_type == "tool":
        tool = obj.get("tool")
        args = obj.get("args", {})
        if not isinstance(tool, str) or not tool.strip():
            return None
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return None
        return {"type": "tool", "tool": tool, "args": args}

    return None


class Agent:
    def __init__(self, llm: OllamaClient | None = None, registry: ToolRegistry | None = None) -> None:
        self.llm = llm or OllamaClient()
        self.registry = registry or get_default_registry()

    async def chat(self, message: str) -> ChatResponse:
        """Single-hop agent: model -> optional tool execution -> structured API response."""
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": message},
        ]

        try:
            raw = await self.llm.generate_chat(messages)
        except OllamaError as exc:
            logger.error("LLM call failed: %s", exc)
            return ChatResponse(type="text", content=f"Model error: {exc}", file=None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected LLM failure")
            return ChatResponse(type="text", content=f"Unexpected model error: {exc}", file=None)

        parsed, fallback = parse_model_json(raw)
        if parsed is None:
            return ChatResponse(type="text", content=fallback or "", file=None)

        validated = _validate_model_payload(parsed)
        if validated is None:
            # Malformed structured output: never crash; surface raw model output.
            return ChatResponse(type="text", content=raw, file=None)

        if validated["type"] == "text":
            return ChatResponse(type="text", content=str(validated["content"]), file=None)

        tool_name = str(validated["tool"])
        args = dict(validated["args"])
        exec_result = await self.registry.execute_async(tool_name, args)
        return self._tool_to_chat_response(tool_name, exec_result)

    def _tool_to_chat_response(self, tool_name: str, exec_result: ToolExecutionResult) -> ChatResponse:
        logger.info("tool finished: %s status=%s", tool_name, exec_result.status)
        payload = exec_result.model_dump(exclude_none=True)
        content = json.dumps(payload, ensure_ascii=False)
        file_path = exec_result.file if exec_result.status == "success" else None
        return ChatResponse(type="tool", content=content, file=file_path)


class AgentService:
    """Process-wide singleton-friendly wrapper (useful for DI / future auth middleware)."""

    def __init__(self) -> None:
        self._agent = Agent()

    @property
    def agent(self) -> Agent:
        return self._agent
