from googleapiclient.errors import HttpError

from google_api import get_calendar_handler


def main():
    try:
        cal_handler = get_calendar_handler()

        calendar_id = cal_handler.get_calendar_id("primary")
        print(f"Primary calendar retrieved: {calendar_id}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
