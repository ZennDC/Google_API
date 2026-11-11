from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from google.auth.exceptions import GoogleAuthError

from ..calendar.handlers import CalendarHandler, EventHandler
from ..gmail.handlers import LabelHandler, MessageHandler
from ..oauth.auth import get_credentials
from ..oauth.factory import CALENDAR_SCOPES, GMAIL_SCOPES
from ._utils import DEFAULT_TIME_ZONE, err
from .calendar_tools import CalendarTools
from .gmail_tools import GmailTools

logger = logging.getLogger("google_api")


class GoogleAPITools:
    """Unified OOP wrapper managing OAuth authentication and LLM-ready tool groups.

    Composes ``GmailTools`` (``self.gmail``) and ``CalendarTools`` (``self.calendar``)
    behind a single OAuth check (``authenticate() -> bool``) and exposes bound agent
    tool methods via ``get_tools()``.
    """

    READ_ONLY_TOOLS: frozenset[str] = GmailTools._discover_tool_names(
        read_only=True
    ) | CalendarTools._discover_tool_names(read_only=True)
    MUTATING_TOOLS: frozenset[str] = GmailTools._discover_tool_names(
        read_only=False
    ) | CalendarTools._discover_tool_names(read_only=False)
    SENSITIVE_TOOLS: frozenset[str] = MUTATING_TOOLS

    def __init__(
        self,
        token_file: str | None = None,
        client_secret_file: str | None = None,
        default_time_zone: str = DEFAULT_TIME_ZONE,
        headless: bool = False,
        save_token: bool = True,
        include_gmail: bool = True,
        include_calendar: bool = True,
        message_handler: MessageHandler | None = None,
        label_handler: LabelHandler | None = None,
        event_handler: EventHandler | None = None,
        calendar_handler: CalendarHandler | None = None,
    ) -> None:
        self.token_file = token_file
        self.client_secret_file = client_secret_file
        self.headless = headless
        self.save_token = save_token
        self.include_gmail = include_gmail
        self.include_calendar = include_calendar

        self._lock = threading.RLock()
        self._credentials: Any = None
        self.last_error: str | None = None

        self.gmail = GmailTools(
            token_file=token_file,
            client_secret_file=client_secret_file,
            headless=headless,
            save_token=save_token,
            message_handler=message_handler,
            label_handler=label_handler,
            lock=self._lock,
            auth_callback=self._ensure_gmail,
        )
        self.calendar = CalendarTools(
            token_file=token_file,
            client_secret_file=client_secret_file,
            default_time_zone=default_time_zone,
            headless=headless,
            save_token=save_token,
            event_handler=event_handler,
            calendar_handler=calendar_handler,
            lock=self._lock,
            auth_callback=self._ensure_calendar,
        )
        self.is_authenticated: bool = self._has_required_handlers()

    @property
    def default_time_zone(self) -> str:
        """Default IANA time zone delegated to ``self.calendar.default_time_zone``."""
        return self.calendar.default_time_zone

    @default_time_zone.setter
    def default_time_zone(self, value: str) -> None:
        self.calendar.default_time_zone = value

    def _has_required_handlers(self) -> bool:
        gmail_ok = (not self.include_gmail) or self.gmail._has_handlers()
        cal_ok = (not self.include_calendar) or self.calendar._has_handlers()
        return (self.include_gmail or self.include_calendar) and gmail_ok and cal_ok

    def _required_scopes(self) -> list[str]:
        scopes: list[str] = []
        if self.include_gmail:
            scopes.extend(GMAIL_SCOPES)
        if self.include_calendar:
            scopes.extend(CALENDAR_SCOPES)
        return scopes

    def authenticate(self) -> bool:
        """Runs unified OAuth authentication and initializes enabled tool groups.

        Returns:
            True if authentication succeeded and all enabled handlers are ready,
            False otherwise (with details stored in ``self.last_error``).
        """
        with self._lock:
            if not self.include_gmail and not self.include_calendar:
                self.last_error = (
                    "At least one of include_gmail or include_calendar must be True."
                )
                self.is_authenticated = False
                return False

            if self._has_required_handlers():
                self.last_error = None
                self.is_authenticated = True
                return True

            try:
                creds = get_credentials(
                    scopes=self._required_scopes(),
                    token_file=self.token_file,
                    client_secret_file=self.client_secret_file,
                    save_token=self.save_token,
                    headless=self.headless,
                )
                self._credentials = creds

                if self.include_gmail:
                    self.gmail._build_handlers_from_credentials(creds)
                    self.gmail.is_authenticated = True
                    self.gmail.last_error = None

                if self.include_calendar:
                    self.calendar._build_handlers_from_credentials(creds)
                    self.calendar.is_authenticated = True
                    self.calendar.last_error = None

                self.last_error = None
                self.is_authenticated = True
                return True
            except (FileNotFoundError, GoogleAuthError, OSError, ValueError) as exc:
                logger.error(f"GoogleAPITools authentication failed: {exc}")
                self.last_error = str(exc)
                self.is_authenticated = False
                return False

    def _ensure_authenticated(self) -> dict[str, Any] | None:
        if self.is_authenticated and self._has_required_handlers():
            return None
        if self.authenticate():
            return None
        return err(self.last_error or "Google API authentication failed.", "AUTH_ERROR")

    def _ensure_gmail(self) -> dict[str, Any] | None:
        if not self.include_gmail:
            return err(
                "Gmail tools are disabled on this GoogleAPITools instance.",
                "INVALID_INPUT",
            )
        return self._ensure_authenticated()

    def _ensure_calendar(self) -> dict[str, Any] | None:
        if not self.include_calendar:
            return err(
                "Calendar tools are disabled on this GoogleAPITools instance.",
                "INVALID_INPUT",
            )
        return self._ensure_authenticated()

    def close(self) -> None:
        """Closes underlying Gmail and Calendar HTTP client resources."""
        with self._lock:
            self.gmail.close()
            self.calendar.close()
            self.is_authenticated = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def get_gmail_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns bound Gmail tool methods if Gmail is enabled."""
        if not self.include_gmail:
            return []
        return self.gmail.get_tools()

    def get_calendar_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns bound Calendar tool methods if Calendar is enabled."""
        if not self.include_calendar:
            return []
        return self.calendar.get_tools()

    def get_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns all enabled bound Gmail and Calendar tool methods."""
        return self.get_gmail_tools() + self.get_calendar_tools()

    def get_read_only_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns bound tool methods marked as read-only for enabled services."""
        tools: list[Callable[..., dict[str, Any]]] = []
        if self.include_gmail:
            tools.extend(self.gmail.get_read_only_tools())
        if self.include_calendar:
            tools.extend(self.calendar.get_read_only_tools())
        return tools

    def get_mutating_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns bound tool methods marked as mutating/sensitive for enabled services."""
        tools: list[Callable[..., dict[str, Any]]] = []
        if self.include_gmail:
            tools.extend(self.gmail.get_mutating_tools())
        if self.include_calendar:
            tools.extend(self.calendar.get_mutating_tools())
        return tools

    def get_tool_metadata(self) -> dict[str, dict[str, bool]]:
        """Returns read-only/mutating metadata keyed by tool name for enabled services."""
        metadata: dict[str, dict[str, bool]] = {}
        if self.include_gmail:
            metadata.update(self.gmail.get_tool_metadata())
        if self.include_calendar:
            metadata.update(self.calendar.get_tool_metadata())
        return metadata

    @classmethod
    def is_read_only(cls, tool: str | Callable[..., Any]) -> bool:
        """Returns True if a tool name or callable is explicitly marked read-only."""
        if callable(tool):
            flag = getattr(tool, "is_read_only", None)
            if isinstance(flag, bool):
                return flag
            return getattr(tool, "__name__", "") in cls.READ_ONLY_TOOLS
        return tool in cls.READ_ONLY_TOOLS

    @classmethod
    def is_mutating(cls, tool: str | Callable[..., Any]) -> bool:
        """Returns True if a tool name or callable is marked mutating/sensitive."""
        if callable(tool):
            flag = getattr(tool, "is_mutating", None)
            if isinstance(flag, bool):
                return flag
            return getattr(tool, "__name__", "") in cls.MUTATING_TOOLS
        return tool in cls.MUTATING_TOOLS
