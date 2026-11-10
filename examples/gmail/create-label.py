from googleapiclient.errors import HttpError

from google_api import get_label_handler


def main():
    try:
        label_handler = get_label_handler()

        label_name = "Example Label"
        if not label_handler.label_exists(label_name):
            label_handler.create_label(label_name)
            print(f'Created label "{label_name}".')
        else:
            print(f'Label "{label_name}" already exists.')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
