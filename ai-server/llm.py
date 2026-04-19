"""Ollama HTTP client (non-streaming today; structured for streaming later)."""

from __future__ import annotations

from typing import Any

import httpx

from config import MAX_TOKENS, MODEL, OLLAMA_TIMEOUT_S, OLLAMA_URL
from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self.base_url = (base_url or OLLAMA_URL).rstrip("/")
        self.model = model or MODEL
        self.timeout_s = timeout_s if timeout_s is not None else OLLAMA_TIMEOUT_S

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> str:
        """
        Call Ollama ``/api/chat`` and return assistant text.

        ``stream=True`` is reserved for future SSE/token streaming; currently unsupported.
        """
        if stream:
            raise NotImplementedError("streaming will be implemented via Ollama stream APIs")

        url = f"{self.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        options: dict[str, Any] = {}
        mt = max_tokens if max_tokens is not None else MAX_TOKENS
        if mt is not None:
            options["num_predict"] = mt
        if options:
            payload["options"] = options

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP error: %s", exc.response.text)
            raise OllamaError(f"Ollama HTTP {exc.response.status_code}: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            logger.error("Ollama request failed: %s", exc)
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise OllamaError("Ollama response missing assistant text")

        return content
