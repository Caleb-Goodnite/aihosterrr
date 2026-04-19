"""Tavily web search tool (API key from ``TAVILY_API_KEY`` env — never commit keys)."""

from __future__ import annotations

from typing import Any

import httpx

from config import TAVILY_API_KEY, TAVILY_TIMEOUT_S
from schemas.tool import ToolExecutionResult
from utils.logger import get_logger

logger = get_logger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_MAX_SNIPPET = 800


def _truncate(s: str, limit: int) -> str:
    s = s.strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


async def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> ToolExecutionResult:
    """
    Run a Tavily search and return a compact JSON-friendly ``details`` payload.

    Authenticates with ``Authorization: Bearer <TAVILY_API_KEY>`` (Tavily Search API).
    """
    if not TAVILY_API_KEY or not str(TAVILY_API_KEY).strip():
        return ToolExecutionResult(
            status="error",
            error="TAVILY_API_KEY is not set. Configure it in the environment (e.g. .env on the server).",
        )

    if not isinstance(query, str) or not query.strip():
        return ToolExecutionResult(status="error", error="query must be a non-empty string")

    try:
        mr = int(max_results)
    except (TypeError, ValueError):
        return ToolExecutionResult(status="error", error="max_results must be an integer")

    mr = max(1, min(mr, 20))

    depth = str(search_depth or "basic").strip().lower()
    allowed_depths = {"basic", "advanced", "fast", "ultra-fast"}
    if depth not in allowed_depths:
        depth = "basic"

    key = str(TAVILY_API_KEY).strip()
    headers = {"Authorization": f"Bearer {key}"}
    body: dict[str, Any] = {
        "query": query.strip(),
        "max_results": mr,
        "search_depth": depth,
        "include_answer": bool(include_answer),
    }

    try:
        async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT_S) as client:
            resp = await client.post(TAVILY_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        # Never echo API key; response text is usually safe JSON error from Tavily.
        body = exc.response.text
        logger.warning("Tavily HTTP %s", exc.response.status_code)
        return ToolExecutionResult(status="error", error=f"Tavily HTTP {exc.response.status_code}: {body[:500]}")
    except httpx.RequestError as exc:
        logger.warning("Tavily request failed: %s", exc)
        return ToolExecutionResult(status="error", error=f"Tavily request failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected Tavily failure")
        return ToolExecutionResult(status="error", error=str(exc))

    if not isinstance(data, dict):
        return ToolExecutionResult(status="error", error="Tavily returned a non-object JSON response")

    results_in = data.get("results")
    if not isinstance(results_in, list):
        results_in = []

    slim_results: list[dict[str, Any]] = []
    for item in results_in[:mr]:
        if not isinstance(item, dict):
            continue
        slim_results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": _truncate(str(item.get("content") or ""), _MAX_SNIPPET),
            }
        )

    details: dict[str, Any] = {
        "query": data.get("query", query.strip()),
        "answer": data.get("answer") if include_answer else None,
        "results": slim_results,
    }

    return ToolExecutionResult(status="success", details=details)
