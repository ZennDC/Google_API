import logging

from .gmail_api import Label, LabelHandler, Message, MessageHandler
from .google_calendar_api import (
    Calendar,
    CalendarHandler,
    CalendarList,
    Event,
    EventHandler,
    TimedEvent,
    convert_date,
    convert_time,
    load_template,
)
from .oauth import (
    CALENDAR_SCOPES,
    GMAIL_SCOPES,
    build_service,
    get_calendar_handler,
    get_calendar_service,
    get_credentials,
    get_credentials_notoken,
    get_event_handler,
    get_gmail_handler,
    get_gmail_service,
    get_label_handler,
    get_message_handler,
)

logging.getLogger("google_api").addHandler(logging.NullHandler())

__all__ = [
    "CALENDAR_SCOPES",
    "GMAIL_SCOPES",
    "Calendar",
    "CalendarHandler",
    "CalendarList",
    "Event",
    "EventHandler",
    "Label",
    "LabelHandler",
    "Message",
    "MessageHandler",
    "TimedEvent",
    "build_service",
    "convert_date",
    "convert_time",
    "load_template",
    "get_calendar_handler",
    "get_calendar_service",
    "get_credentials",
    "get_credentials_notoken",
    "get_event_handler",
    "get_gmail_handler",
    "get_gmail_service",
    "get_label_handler",
    "get_message_handler",
]
