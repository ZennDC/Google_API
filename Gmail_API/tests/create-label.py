from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Gmail_API.handlers import LabelHandler
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.labels"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)
        label_handler = LabelHandler(service)

        label_name = "Example Label"
        if not label_handler.label_exists(label_name):
            label_handler.create_label(label_name)
        else:
            print(f'Label "{label_name}" already exists.')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
