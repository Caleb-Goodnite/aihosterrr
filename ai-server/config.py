"""Application configuration (model, Ollama, runtime flags).

Environment variables override defaults for deployment flexibility.
"""

from __future__ import annotations

import os
from pathlib import Path

# Default model aligned with project requirements (Ollama tag may vary by pull).
MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Ollama HTTP API base URL (no trailing slash).
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

# Optional generation cap; None lets Ollama use its defaults.
_max_raw = os.getenv("MAX_TOKENS", "").strip()
MAX_TOKENS: int | None = int(_max_raw) if _max_raw else None

DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "on")

# All tool-generated files are confined under this directory.
WORK_DIR: Path = Path(os.getenv("AI_SERVER_WORK_DIR", "generated_files")).resolve()

# HTTP timeouts for Ollama (local inference can be slow on CPU).
OLLAMA_TIMEOUT_S: float = float(os.getenv("OLLAMA_TIMEOUT_S", "600"))

# Tavily Search (https://tavily.com) — set on the server only; never commit real keys.
TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY") or None
TAVILY_TIMEOUT_S: float = float(os.getenv("TAVILY_TIMEOUT_S", "60"))
