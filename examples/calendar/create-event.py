import datetime

from googleapiclient.errors import HttpError

from google_api import TimedEvent, get_event_handler


def main():
    try:
        event_handler = get_event_handler()

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

        created = event_handler.plan_event("primary", event_obj)
        print(
            f"Event created successfully! Summary: '{created.get('summary')}', ID: {created.get('id')}"
        )

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
