from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError

logger = logging.getLogger("google_api")

DEFAULT_TIME_ZONE = "Europe/Brussels"

TOOL_HANDLED_ERRORS = (
    ValueError,
    KeyError,
    HttpError,
    FileNotFoundError,
    GoogleAuthError,
    OSError,
)

_HTML_TAG_PATTERN = re.compile(
    r"<\s*(?:!doctype|html|head|body|div|p|br|table|tr|td|span|a\s|style|script|ul|ol|li|h[1-6])\b",
    re.IGNORECASE,
)
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }
)
_IGNORED_TAGS = frozenset({"script", "style", "head"})


class _HTMLTextExtractor(HTMLParser):
    """Lightweight HTML-to-text extractor built on the Python standard library."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in _IGNORED_TAGS:
            self._ignore_depth += 1
            return
        if self._ignore_depth == 0 and tag_lower in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in _IGNORED_TAGS:
            if self._ignore_depth > 0:
                self._ignore_depth -= 1
            return
        if self._ignore_depth == 0 and tag_lower in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignore_depth == 0:
            self._chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self._chunks)
        lines = [line.strip() for line in raw.splitlines()]
        collapsed = "\n".join(lines)
        return _MULTI_NEWLINE_PATTERN.sub("\n\n", collapsed).strip()


def ok(data: dict[str, Any], message: str) -> dict[str, Any]:
    """Builds a standard success envelope for tool responses."""
    return {
        "success": True,
        "data": data,
        "message": message,
    }


def err(error: str, error_code: str) -> dict[str, Any]:
    """Builds a standard error envelope for tool responses."""
    return {
        "success": False,
        "error": error,
        "error_code": error_code,
    }


def _extract_http_status(error: HttpError) -> int | None:
    resp = getattr(error, "resp", None)
    status = getattr(resp, "status", None)
    if status is None:
        return None
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def handle_tool_exception(exc: Exception, context: str = "") -> dict[str, Any]:
    """Converts common validation, auth, and Google API errors into compact LLM error payloads."""
    prefix = f"{context}: " if context else ""

    if isinstance(exc, (ValueError, KeyError)):
        msg = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        return err(f"{prefix}{msg}", "INVALID_INPUT")

    if isinstance(exc, HttpError):
        status = _extract_http_status(exc)
        if status == 404:
            code = "NOT_FOUND"
        elif status in (401, 403):
            code = "PERMISSION_DENIED"
        elif status == 429:
            code = "RATE_LIMITED"
        else:
            code = "API_ERROR"
        logger.warning(f"{prefix}Google API error ({status}): {exc}")
        return err(f"{prefix}{exc}", code)

    if isinstance(exc, (FileNotFoundError, GoogleAuthError)):
        logger.error(f"{prefix}Authentication error: {exc}")
        return err(f"{prefix}{exc}", "AUTH_ERROR")

    logger.exception(f"{prefix}Unexpected tool error: {exc}")
    return err(f"{prefix}{exc}", "INTERNAL_ERROR")


def looks_like_html(text: str) -> bool:
    """Returns True when text appears to contain HTML markup."""
    return bool(_HTML_TAG_PATTERN.search(text))


def strip_html(raw_html: str) -> str:
    """Strips HTML tags, scripts, and styles and returns normalized plain text."""
    parser = _HTMLTextExtractor()
    parser.feed(raw_html)
    parser.close()
    return html.unescape(parser.get_text())


def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    """Truncates text to at most max_chars characters, returning (text, was_truncated)."""
    if max_chars <= 0:
        raise ValueError("max_body_chars must be greater than 0.")
    if len(text) <= max_chars:
        return text, False
    return f"{text[:max_chars].rstrip()}\n[... truncated]", True


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    """Clamps an integer into the inclusive [minimum, maximum] range."""
    return max(minimum, min(maximum, value))


def epoch_ms_to_iso(internal_date_ms: int) -> str:
    """Converts a Unix millisecond timestamp to an ISO-8601 UTC string."""
    if internal_date_ms <= 0:
        return ""
    dt = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_datetime(value: str, time_zone: str) -> tuple[datetime, bool]:
    """Parses an ISO-8601 date or datetime string in the given IANA time zone.

    Supports 'YYYY-MM-DD' (returns is_date_only=True) and full ISO datetimes
    including trailing 'Z' on Python 3.10+.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("Date/time string cannot be empty.")

    try:
        tz = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Invalid IANA time zone: '{time_zone}'.") from exc

    if _ISO_DATE_PATTERN.match(stripped):
        parsed_date = datetime.strptime(stripped, "%Y-%m-%d")
        return parsed_date.replace(tzinfo=tz), True

    normalized = f"{stripped[:-1]}+00:00" if stripped.endswith(("Z", "z")) else stripped
    try:
        parsed_dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Invalid ISO-8601 date/time '{value}'. Expected 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM[:SS]'."
        ) from exc

    if parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=tz)
    return parsed_dt, False
