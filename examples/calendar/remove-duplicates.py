import datetime

from googleapiclient.errors import HttpError

from google_api import get_event_handler


def main():
    try:
        event_handler = get_event_handler()

        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime(
            "%d/%m/%Y"
        )
        print(f"Checking for and removing duplicates on: {tomorrow}")
        event_handler.remove_duplicates("primary", tomorrow)
        print("Duplicate check complete.")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
