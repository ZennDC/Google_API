import logging

# Central top-level logger for the entire google_api library
logger = logging.getLogger("google_api")

# NullHandler avoids "No handler found" warnings when caller has not configured logging
logger.addHandler(logging.NullHandler())
