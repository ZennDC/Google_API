from googleapiclient.errors import HttpError

from google_api import Calendar, get_calendar_handler


def main():
    try:
        cal_handler = get_calendar_handler()

        calendar_name = "Test Calendar"
        existing_id = cal_handler.get_calendar_id(calendar_name)
        if existing_id:
            print(f'Calendar "{calendar_name}" already exists with ID: {existing_id}')
        else:
            new_calendar = Calendar(calendar_name).build()
            new_id = cal_handler.create_calendar(new_calendar)
            print(f'Created calendar "{calendar_name}" with ID: {new_id}')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
