"""Tool definitions, dispatcher, and registry for extensibility."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from schemas.tool import ToolExecutionResult, ToolSpec
from tools import file_tools, tavily_tool
from utils.logger import get_logger

logger = get_logger(__name__)

ToolHandler = Callable[..., ToolExecutionResult] | Callable[..., Awaitable[ToolExecutionResult]]


def tool_catalog() -> list[ToolSpec]:
    """Declarative catalog used in prompts and for future OpenAPI/tool-schema export."""
    return [
        ToolSpec(
            name="write_file",
            description="Write arbitrary UTF-8 text to a file under the server output directory.",
            args_schema={
                "type": "object",
                "required": ["filename", "content"],
                "properties": {
                    "filename": {"type": "string", "description": "Basename only, any allowed extension."},
                    "content": {"type": "string"},
                },
            },
        ),
        ToolSpec(
            name="create_markdown",
            description="Create a Markdown (.md) document under the server output directory.",
            args_schema={
                "type": "object",
                "required": ["filename", "content"],
                "properties": {
                    "filename": {"type": "string", "description": "Must end with .md"},
                    "content": {"type": "string"},
                },
            },
        ),
        ToolSpec(
            name="create_pdf",
            description="Create a simple text PDF using ReportLab under the server output directory.",
            args_schema={
                "type": "object",
                "required": ["filename", "content"],
                "properties": {
                    "filename": {"type": "string", "description": "Must end with .pdf"},
                    "content": {"type": "string", "description": "Multi-line plain text body"},
                },
            },
        ),
        ToolSpec(
            name="create_excel",
            description="Create an .xlsx spreadsheet from a 2D array (rows of cells).",
            args_schema={
                "type": "object",
                "required": ["filename", "data"],
                "properties": {
                    "filename": {"type": "string", "description": "Must end with .xlsx"},
                    "data": {
                        "type": "array",
                        "items": {"type": "array"},
                        "description": "Non-empty list of rows; each row is a list of string/number values",
                    },
                },
            },
        ),
        ToolSpec(
            name="tavily_search",
            description="Search the public web via Tavily. Requires TAVILY_API_KEY on the server.",
            args_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "1–20, default 5"},
                    "search_depth": {
                        "type": "string",
                        "description": "basic | advanced | fast | ultra-fast (default basic)",
                    },
                    "include_answer": {
                        "type": "boolean",
                        "description": "Whether to ask Tavily for a short synthesized answer (default true)",
                    },
                },
            },
        ),
    ]


def _catalog_by_name() -> dict[str, ToolSpec]:
    return {t.name: t for t in tool_catalog()}


class ToolRegistry:
    """
    Central dispatcher.

    Designed for extension:
    - register(name, handler)
    - optional async handlers (awaited by agent if needed)
    """

    def __init__(self, handlers: Mapping[str, ToolHandler] | None = None) -> None:
        self._handlers: dict[str, ToolHandler] = dict(handlers or {})
        self._specs = _catalog_by_name()

    def register(self, name: str, handler: ToolHandler) -> None:
        self._handlers[name] = handler
        logger.info("registered tool handler: %s", name)

    def has(self, name: str) -> bool:
        return name in self._handlers

    async def execute_async(self, name: str, args: dict[str, Any]) -> ToolExecutionResult:
        if name not in self._handlers:
            return ToolExecutionResult(status="error", error=f"unknown tool: {name}")

        if name not in self._specs:
            # Still allow dynamically registered tools without catalog entries.
            logger.debug("executing dynamic tool without catalog entry: %s", name)

        handler = self._handlers[name]
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(**args)  # type: ignore[misc]
            else:
                result = handler(**args)  # type: ignore[misc]
            if isinstance(result, ToolExecutionResult):
                return result
            return ToolExecutionResult(status="error", error="tool handler returned invalid type")
        except TypeError as exc:
            logger.exception("tool argument validation failed: %s", name)
            return ToolExecutionResult(status="error", error=str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("tool execution crashed: %s", name)
            return ToolExecutionResult(status="error", error=str(exc))


def get_default_registry() -> ToolRegistry:
    reg = ToolRegistry(
        {
            "write_file": file_tools.write_file,
            "create_markdown": file_tools.create_markdown,
            "create_pdf": file_tools.create_pdf,
            "create_excel": file_tools.create_excel,
            "tavily_search": tavily_tool.tavily_search,
        }
    )
    return reg


def tools_prompt_json_schema() -> str:
    """Human-readable JSON schema summary for system prompts."""
    lines: list[str] = []
    for spec in tool_catalog():
        lines.append(f"- {spec.name}: {spec.description}")
        lines.append(f"  args_schema: {spec.args_schema}")
    return "\n".join(lines)
