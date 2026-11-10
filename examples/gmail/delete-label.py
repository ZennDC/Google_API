from googleapiclient.errors import HttpError

from google_api import get_label_handler


def main():
    try:
        label_handler = get_label_handler()

        label_name = "Example Label"
        label_id = label_handler.get_label_id(label_name)
        if label_id:
            label_handler.delete_label(label_id)
            print(f"Label with ID: {label_id} deleted successfully.")
        else:
            print(f'Label "{label_name}" not found.')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
