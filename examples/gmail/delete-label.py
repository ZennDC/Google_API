from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_api.handlers import LabelHandler
from oauth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.labels"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)
        label_handler = LabelHandler(service)

        label_name = "Example Label"
        label_id = label_handler.get_label_id(label_name)
        if label_id:
            label_handler.delete_label(label_id)
            print(f'Label with ID: {label_id} deleted successfully.')
        else:
            print(f'Label "{label_name}" not found.')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
