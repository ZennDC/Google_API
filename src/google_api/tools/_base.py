from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from google.auth.exceptions import GoogleAuthError

from ..oauth.auth import get_credentials
from ._utils import err

logger = logging.getLogger("google_api")


class _BaseToolGroup:
    """Shared OAuth, thread-locking, and resource-cleanup lifecycle for tool classes."""

    def __init__(
        self,
        token_file: str | None = None,
        client_secret_file: str | None = None,
        headless: bool = False,
        save_token: bool = True,
        lock: Any | None = None,
        auth_callback: Callable[[], dict[str, Any] | None] | None = None,
    ) -> None:
        self.token_file = token_file
        self.client_secret_file = client_secret_file
        self.headless = headless
        self.save_token = save_token
        self._lock = lock if lock is not None else threading.RLock()
        self._auth_callback = auth_callback
        self._credentials: Any = None
        self.last_error: str | None = None
        self.is_authenticated: bool = False

    def _required_scopes(self) -> list[str]:
        raise NotImplementedError

    def _has_handlers(self) -> bool:
        raise NotImplementedError

    def _build_handlers_from_credentials(self, creds: Any) -> None:
        raise NotImplementedError

    def _iter_handlers(self) -> tuple[Any, ...]:
        raise NotImplementedError

    def _clear_handlers(self) -> None:
        raise NotImplementedError

    def authenticate(self) -> bool:
        """Runs OAuth authentication and initializes handlers for this tool group.

        Returns:
            True if authentication succeeded and handlers are ready, False otherwise.
        """
        with self._lock:
            if self._has_handlers():
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
                self._build_handlers_from_credentials(creds)
                self.last_error = None
                self.is_authenticated = True
                return True
            except (FileNotFoundError, GoogleAuthError, OSError, ValueError) as exc:
                logger.error(f"{type(self).__name__} authentication failed: {exc}")
                self.last_error = str(exc)
                self.is_authenticated = False
                return False

    def _ensure_ready(self) -> dict[str, Any] | None:
        if self._auth_callback is not None:
            return self._auth_callback()
        if self.is_authenticated and self._has_handlers():
            return None
        if self.authenticate():
            return None
        return err(self.last_error or "Google API authentication failed.", "AUTH_ERROR")

    def close(self) -> None:
        """Closes underlying Google API HTTP client resources."""
        with self._lock:
            seen_services: set[int] = set()
            for handler in self._iter_handlers():
                if handler is None:
                    continue
                service = getattr(handler, "service", None)
                if service is not None and id(service) in seen_services:
                    continue
                if service is not None:
                    seen_services.add(id(service))
                if hasattr(handler, "close"):
                    handler.close()

            self._clear_handlers()
            self.is_authenticated = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
