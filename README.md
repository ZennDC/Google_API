# Google-API

A clean, modern, and Pythonic wrapper for Google Gmail and Calendar APIs by ZennDC.

[![CI](https://github.com/ZennDC/google-api/actions/workflows/ci.yml/badge.svg)](https://github.com/ZennDC/google-api/actions/workflows/ci.yml)
[![Python: >=3.10](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type: PEP 561](https://img.shields.io/badge/typing-typed-informational.svg)](https://peps.python.org/pep-0561/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## Features

- **Encapsulated OAuth & Factory**:
  - Automatically manages default scopes (`GMAIL_SCOPES`, `CALENDAR_SCOPES`).
  - Desktop OAuth with automatic local redirect web server.
  - Headless / remote server / Docker support with console copy-paste (`headless=True` or `GOOGLE_API_HEADLESS=1`).
  - Token persistence and silent background refresh.
  - In-memory credential option without disk persistence (`get_credentials_notoken`).
- **Gmail Automation (`google_api.gmail`)**:
  - **`MessageHandler`**: Search queries, paginated message iteration (`iter_messages`), structured metadata extraction, MIME body decoding (plain text & HTML fallback), message composition, drafts creation, batch modification, batch deletion, and trash/untrash actions.
  - **`LabelHandler`**: Complete label CRUD, system vs. user label inspection, label visibility, and automatic color mapping.
- **Calendar Automation (`google_api.calendar`)**:
  - **`EventHandler`**: Event creation (`plan_event`), pagination (`iter_events`), Dutch/ISO date and time conversions, recurrence support, and duplicate detection/cleanup.
  - **`CalendarHandler`**: Primary and secondary calendar CRUD, calendar list entry management, and ID resolution by summary name.
- **Developer-Ready Architecture**:
  - Full PEP 561 typed (`py.typed`).
  - Comprehensive unit test suite with 100% offline mocks.
  - Clean `src/` layout configured with `hatchling`.

---

## Installation

### Directly from GitHub (for use in other projects)

```bash
pip install git+https://github.com/ZennDC/google-api.git
```

To install a specific branch or release tag:
```bash
pip install git+https://github.com/ZennDC/google-api.git@v1.0.0
```

### For Local Development

Clone the repository and install in editable mode:
```bash
pip install -e .
```

To include test and lint dependencies:
```bash
pip install -e ".[dev]"
```

---

## Prerequisites: Google Cloud Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project, and enable the **Gmail API** and **Google Calendar API**.
3. Configure the **OAuth consent screen** and create OAuth 2.0 Client IDs (Application Type: **Desktop app**).
4. Download the client secret JSON file and place it in your workspace root as `client_secret.json` (or set the file path via `client_secret_file="..."`).

---

## Quickstart Examples

### 1. Gmail: Read Recent Emails

```python
from google_api import get_message_handler

# Scopes and service construction are handled automatically
handler = get_message_handler()

for msg_id in handler.iter_messages(query="is:unread", max_results=5):
    sender = handler.get_sender_address(msg_id)
    subject = handler.get_subject(msg_id)
    print(f"[{sender}] {subject}")
```

### 2. Gmail: Manage Labels

```python
from google_api import get_label_handler

label_handler = get_label_handler()

# Automatically creates the label if it doesn't already exist
label_id = label_handler.get_or_create_label_id("Automated")
print(f"Label ready with ID: {label_id}")
```

### 3. Calendar: Plan a New Event

```python
import datetime
from google_api import TimedEvent, get_event_handler

event_handler = get_event_handler()

tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d/%m/%Y")

event = TimedEvent(
    summary="Project Review",
    start_date=tomorrow,
    start_time="14:00",
    end_date=tomorrow,
    end_time="15:30",
    time_format="%H:%M",
)
event.description = "Automated event planned via Google_API"

created = event_handler.plan_event("primary", event.build())
print(f"Created event: {created.get('id')}")
```

### 4. OAuth: Headless / Docker / SSH

When a web browser cannot automatically open:

```python
from google_api import get_credentials, GMAIL_SCOPES

creds = get_credentials(scopes=GMAIL_SCOPES, headless=True)
```
*Or simply set the environment variable:*
```bash
export GOOGLE_API_HEADLESS=1
```

---

## Project Structure

```
├── examples/
│   ├── calendar/      # Calendar quickstart, event planning & duplicate removal
│   ├── gmail/         # Gmail reading, search, pagination & label examples
│   └── oauth/         # Local browser flow, headless flow & in-memory auth
├── src/google_api/
│   ├── calendar/      # Calendar & event handlers, models, and JSON templates
│   ├── gmail/         # Message & label handlers, message/label objects
│   ├── oauth/         # Credentials discovery, flow handlers & factory builders
│   ├── py.typed       # PEP 561 marker
│   └── __init__.py    # Top-level API exports
├── tests/             # Offline unit test suites (Calendar, Gmail, OAuth)
└── pyproject.toml     # Packaging and dependency specification (PEP 621)
```

---

## Running Tests

All unit tests run completely offline without needing real Google API credentials or network access:

```bash
pytest -v
```

Code quality and formatting checks:

```bash
ruff check src/ tests/ examples/
ruff format --check src/ tests/ examples/
```

---

## License

This project is licensed under the [MIT License](LICENSE).
