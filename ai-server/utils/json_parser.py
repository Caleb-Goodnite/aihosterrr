"""Robust JSON extraction from LLM outputs with safe fallbacks."""

from __future__ import annotations

import json
import re
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    m = _JSON_FENCE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _extract_balanced_object(text: str) -> str | None:
    """Best-effort: find first `{` and matching closing `}` by brace depth."""
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string: str | None = None
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue

        if ch in ("'", '"'):
            in_string = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def parse_model_json(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Parse structured JSON from model output.

    Returns:
        (payload, None) on success
        (None, fallback_text) when no safe JSON object could be parsed
    """
    if raw is None:
        return None, ""

    text = raw.strip()
    if not text:
        return None, ""

    candidates: list[str] = []
    candidates.append(text)
    candidates.append(_strip_code_fences(text))

    seen: set[str] = set()
    for cand in candidates:
        cand = cand.strip()
        if not cand or cand in seen:
            continue
        seen.add(cand)

        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj, None
        except json.JSONDecodeError:
            logger.debug("json.loads failed for candidate snippet", exc_info=DEBUG)

        balanced = _extract_balanced_object(cand)
        if balanced and balanced not in seen:
            seen.add(balanced)
            try:
                obj = json.loads(balanced)
                if isinstance(obj, dict):
                    return obj, None
            except json.JSONDecodeError:
                logger.debug("json.loads failed for balanced object", exc_info=DEBUG)

    return None, raw
