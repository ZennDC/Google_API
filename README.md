# Google-API

A Google API implementation by ZennDC.

## Features

- **OAuth & Credentials**:
  - Desktop authentication with automatic local redirect server.
  - Headless / Docker authentication support via manual console code copy-paste (`headless=True` or `GOOGLE_API_HEADLESS=1`).
  - Customizable port, host, and bind address (`port`, `host`, `bind_addr`).
  - Automatic token persistence and refresh.
- **Automatic Service & Handler Factory**:
  - `build_service(service_name, version, ...)`: Build any authorized Google API discovery service under the hood.
  - `get_gmail_handler()` / `get_message_handler()` / `get_label_handler()`: Instantiate Gmail handlers with automated credential retrieval.
  - `get_calendar_handler()` / `get_event_handler()`: Instantiate Google Calendar handlers directly.
- **Gmail API**: Complete message and label management.
- **Google Calendar API**: Event planning, recurrence handling, calendar management.

## Quickstart

### Using the Automatic Handler Factory

```python
from google_api import get_message_handler, get_calendar_handler

# Initializes credentials and Gmail v1 service under the hood
message_handler = get_message_handler()
for msg_id in message_handler.iter_messages(max_results=10):
    print(msg_id)

# Initializes credentials and Calendar v3 service under the hood
calendar_handler = get_calendar_handler()
```

### Headless / Docker Authentication

When running in headless environments (e.g., Docker, SSH, remote VM):

```python
from google_api import get_credentials

# Prompts for manual authorization code paste in the console
creds = get_credentials(scopes=["https://www.googleapis.com/auth/gmail.readonly"], headless=True)
```

Or set the environment variable:
```bash
export GOOGLE_API_HEADLESS=1
```

