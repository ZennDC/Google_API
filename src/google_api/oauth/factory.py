import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from .auth import get_credentials

logger = logging.getLogger("google_api")

# Standard default scopes for Gmail and Google Calendar
GMAIL_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
]

CALENDAR_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/calendar",
]


def build_service(
    service_name: str,
    version: str,
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    token_file: str | None = None,
    client_secret_file: str | None = None,
    save_token: bool = True,
    headless: bool = False,
    port: int = 0,
    host: str = "localhost",
    bind_addr: str | None = None,
    open_browser: bool | None = None,
    **kwargs: Any,
) -> Resource:
    """Builds and returns an authorized Google API service Resource.

    If ``credentials`` is not explicitly provided, ``get_credentials`` is invoked
    under the hood using the provided scopes and OAuth configuration options.

    Args:
        service_name: Name of the service (e.g. 'gmail', 'calendar').
        version: API version (e.g. 'v1', 'v3').
        scopes: OAuth scopes required. If None, service-specific defaults are used when available.
        credentials: Optional pre-existing Credentials instance.
        token_file: Path to token storage file.
        client_secret_file: Path to client_secret.json.
        save_token: Whether to save/load tokens from disk.
        headless: Whether to use headless manual console flow.
        port: Redirect server port.
        host: Redirect server host.
        bind_addr: Redirect server bind address.
        open_browser: Whether to launch browser automatically.
        **kwargs: Additional parameters passed through to googleapiclient.discovery.build.

    Returns:
        Authorized googleapiclient Resource.
    """
    if credentials is None:
        if scopes is None:
            if service_name.lower() == "gmail":
                scopes = GMAIL_SCOPES
            elif service_name.lower() == "calendar":
                scopes = CALENDAR_SCOPES
            else:
                raise ValueError(
                    f"Scopes must be specified when building service '{service_name}'."
                )

        credentials = get_credentials(
            scopes=scopes,
            token_file=token_file,
            client_secret_file=client_secret_file,
            save_token=save_token,
            headless=headless,
            port=port,
            host=host,
            bind_addr=bind_addr,
            open_browser=open_browser,
        )

    logger.debug(f"Building Google API service: {service_name} {version}")
    return build(service_name, version, credentials=credentials, **kwargs)


def get_gmail_service(
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    **kwargs: Any,
) -> Resource:
    """Builds and returns an authorized Gmail v1 service Resource."""
    return build_service(
        service_name="gmail",
        version="v1",
        scopes=scopes if scopes is not None else GMAIL_SCOPES,
        credentials=credentials,
        **kwargs,
    )


def get_calendar_service(
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    **kwargs: Any,
) -> Resource:
    """Builds and returns an authorized Calendar v3 service Resource."""
    return build_service(
        service_name="calendar",
        version="v3",
        scopes=scopes if scopes is not None else CALENDAR_SCOPES,
        credentials=credentials,
        **kwargs,
    )


def get_gmail_handler(
    handler_type: str = "message",
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    service: Resource | None = None,
    **kwargs: Any,
):
    """Convenience factory returning an initialized Gmail MessageHandler or LabelHandler.

    Args:
        handler_type: 'message' for MessageHandler or 'label' for LabelHandler.
        scopes: Custom OAuth scopes (defaults to GMAIL_SCOPES).
        credentials: Optional pre-existing Credentials instance.
        service: Optional pre-existing Gmail Resource service.
        **kwargs: Additional arguments passed to the handler or build_service.
    """
    from ..gmail.handlers import LabelHandler, MessageHandler

    handler_type_lower = handler_type.lower()
    if handler_type_lower not in ("message", "label"):
        raise ValueError(
            f"Unknown handler_type '{handler_type}'. Must be 'message' or 'label'."
        )

    # Extract handler-specific keyword arguments
    handler_kwargs = {}
    if handler_type_lower == "message" and "include_spam_trash" in kwargs:
        handler_kwargs["include_spam_trash"] = kwargs.pop("include_spam_trash")

    if service is None:
        service = get_gmail_service(scopes=scopes, credentials=credentials, **kwargs)

    if handler_type_lower == "message":
        return MessageHandler(service, **handler_kwargs)
    return LabelHandler(service, **handler_kwargs)


def get_message_handler(
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    service: Resource | None = None,
    include_spam_trash: bool = False,
    **kwargs: Any,
):
    """Convenience factory returning an initialized MessageHandler."""
    return get_gmail_handler(
        handler_type="message",
        scopes=scopes,
        credentials=credentials,
        service=service,
        include_spam_trash=include_spam_trash,
        **kwargs,
    )


def get_label_handler(
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    service: Resource | None = None,
    **kwargs: Any,
):
    """Convenience factory returning an initialized LabelHandler."""
    return get_gmail_handler(
        handler_type="label",
        scopes=scopes,
        credentials=credentials,
        service=service,
        **kwargs,
    )


def get_calendar_handler(
    handler_type: str = "event",
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    service: Resource | None = None,
    **kwargs: Any,
):
    """Convenience factory returning an initialized EventHandler or CalendarHandler.

    Args:
        handler_type: 'event' for EventHandler or 'calendar' for CalendarHandler.
        scopes: Custom OAuth scopes (defaults to CALENDAR_SCOPES).
        credentials: Optional pre-existing Credentials instance.
        service: Optional pre-existing Calendar Resource service.
        **kwargs: Additional arguments passed to the handler or build_service.
    """
    from ..calendar.handlers import CalendarHandler, EventHandler

    handler_type_lower = handler_type.lower()
    if handler_type_lower not in ("event", "calendar"):
        raise ValueError(
            f"Unknown handler_type '{handler_type}'. Must be 'event' or 'calendar'."
        )

    if service is None:
        service = get_calendar_service(scopes=scopes, credentials=credentials, **kwargs)

    if handler_type_lower == "event":
        return EventHandler(service)
    return CalendarHandler(service)


def get_event_handler(
    scopes: list[str] | None = None,
    credentials: Credentials | None = None,
    service: Resource | None = None,
    **kwargs: Any,
):
    """Convenience factory returning an initialized EventHandler."""
    return get_calendar_handler(
        handler_type="event",
        scopes=scopes,
        credentials=credentials,
        service=service,
        **kwargs,
    )
