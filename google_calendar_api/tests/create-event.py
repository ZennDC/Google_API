import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_calendar_api.handlers import EventHandler
from google_calendar_api.objects import TimedEvent
from oauth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("calendar", "v3", credentials=creds)
        event_handler = EventHandler(service)

        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        date_str = tomorrow.strftime("%d/%m/%Y")

        event = TimedEvent(
            summary="API Test Event",
            start_date=date_str,
            start_time="14:00",
            end_date=date_str,
            end_time="15:00",
            time_format="%H:%M",
        )
        event.description = "Automated test event created via Google_API"
        event_obj = event.build()

        created = event_handler.planEvent("primary", event_obj)
        print(
            f"Event created successfully! Summary: '{created.get('summary')}', ID: {created.get('id')}"
        )

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
