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
)
from .oauth import get_credentials, get_credentials_notoken

# Set a NullHandler on the top-level logger to prevent unconfigured logging warnings
logging.getLogger("google_api").addHandler(logging.NullHandler())

__all__ = [
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
    "convert_date",
    "convert_time",
    "get_credentials",
    "get_credentials_notoken",
]
