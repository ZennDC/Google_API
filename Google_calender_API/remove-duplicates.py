from Google_API.Login.Credentials import get_credentials as get_creds
from Handlers import CalendarHandler
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Set up credentials and initialize the Google Calendar API client
creds = get_creds('token.json', 'credentials.json', SCOPES)
service = build('calendar', 'v3', credentials=creds)

handler = CalendarHandler(service)

# Fetch events from the calendar
calendar_name = 'Werk'
calendar_id = handler.get_calendar_id(calendar_name)
events_result = service.events().list(calendarId=calendar_id, timeMin='2022-01-01T00:00:00Z', timeMax='2024-12-31T23:59:59Z').execute()
events = events_result.get('items', [])

# Find and remove duplicates
seen_events = {}
for event in events:
    event_key = (event['summary'], event['start'].get('dateTime'), event['end'].get('dateTime'))
    if event_key in seen_events:
        # Duplicate found, remove this event
        service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
    else:
        # No duplicate, add to seen events
        seen_events[event_key] = event

print("Duplicate events removed.")
