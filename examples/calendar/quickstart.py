import datetime

from googleapiclient.errors import HttpError

from google_api import get_calendar_service


def main():
    """Shows basic usage of the Google Calendar API by listing the next 10 upcoming events."""
    try:
        service = get_calendar_service()

        now = datetime.datetime.now(tz=datetime.UTC).isoformat()
        print("Getting the upcoming 10 events...")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"{start} - {event.get('summary', '(No title)')}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
