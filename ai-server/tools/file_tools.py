"""Filesystem-backed tools (text, markdown, PDF, Excel).

Security: outputs are always resolved under ``config.WORK_DIR`` using basename-only names.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from config import WORK_DIR
from schemas.tool import ToolExecutionResult
from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_BASENAME_LEN = 200
_SAFE_NAME_RE = re.compile(r"^[\w.\- ]+$")


def ensure_workdir() -> Path:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    return WORK_DIR


def sanitize_filename(filename: str) -> str:
    """
    Reduce path traversal risk: only basename, constrained charset, length cap.
    """
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must be a non-empty string")

    raw = filename.strip()
    normalized = raw.replace("\\", "/")
    if ".." in normalized or normalized.startswith("/"):
        raise ValueError("filename must not contain path traversal patterns")

    name = Path(filename).name.strip()
    if not name or name in (".", ".."):
        raise ValueError("invalid filename")

    if len(name) > _MAX_BASENAME_LEN:
        raise ValueError("filename is too long")

    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("filename must not contain path separators")

    if not _SAFE_NAME_RE.match(name):
        raise ValueError("filename contains disallowed characters")

    return name


def safe_target_path(filename: str) -> Path:
    base = ensure_workdir().resolve()
    safe_name = sanitize_filename(filename)
    target = (base / safe_name).resolve()
    if not target.is_relative_to(base):
        raise ValueError("refusing to write outside working directory")
    return target


def write_file(filename: str, content: str) -> ToolExecutionResult:
    try:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        path = safe_target_path(filename)
        path.write_text(content, encoding="utf-8")
        return ToolExecutionResult(status="success", file=str(path))
    except Exception as exc:  # noqa: BLE001 - tool boundary must not raise
        logger.exception("write_file failed")
        return ToolExecutionResult(status="error", error=str(exc))


def create_markdown(filename: str, content: str) -> ToolExecutionResult:
    try:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        name = sanitize_filename(filename)
        if not name.lower().endswith(".md"):
            raise ValueError("create_markdown requires a .md filename")
        path = safe_target_path(name)
        path.write_text(content, encoding="utf-8")
        return ToolExecutionResult(status="success", file=str(path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_markdown failed")
        return ToolExecutionResult(status="error", error=str(exc))


def create_pdf(filename: str, content: str) -> ToolExecutionResult:
    try:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        name = sanitize_filename(filename)
        if not name.lower().endswith(".pdf"):
            raise ValueError("create_pdf requires a .pdf filename")

        path = safe_target_path(name)

        c = canvas.Canvas(str(path), pagesize=letter)
        width, height = letter

        text_object = c.beginText(40, height - 50)
        text_object.setFont("Helvetica", 11)

        max_chars = 110
        for raw_line in content.splitlines():
            line = raw_line.replace("\t", "    ")
            if not line:
                text_object.textLine("")
                continue

            start = 0
            while start < len(line):
                chunk = line[start : start + max_chars]
                text_object.textLine(chunk)
                start += max_chars

                if text_object.getY() < 50:
                    c.drawText(text_object)
                    c.showPage()
                    text_object = c.beginText(40, height - 50)
                    text_object.setFont("Helvetica", 11)

        c.drawText(text_object)
        c.save()

        return ToolExecutionResult(status="success", file=str(path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_pdf failed")
        return ToolExecutionResult(status="error", error=str(exc))


def create_excel(filename: str, data: Any) -> ToolExecutionResult:
    try:
        name = sanitize_filename(filename)
        if not name.lower().endswith(".xlsx"):
            raise ValueError("create_excel requires a .xlsx filename")

        if not isinstance(data, list) or not data:
            raise TypeError("data must be a non-empty list of rows")

        for idx, row in enumerate(data):
            if not isinstance(row, list):
                raise TypeError(f"row {idx} must be a list")

        path = safe_target_path(name)
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        for row in data:
            ws.append(row)
        wb.save(str(path))

        return ToolExecutionResult(status="success", file=str(path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_excel failed")
        return ToolExecutionResult(status="error", error=str(exc))
