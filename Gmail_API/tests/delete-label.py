from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Gmail_API.handlers import LabelHandler
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.labels"]


def delete_label(service, label_id):
    """Deletes a label in the user's mailbox."""
    service.users().labels().delete(userId="me", id=label_id).execute()
    print(f"Label with ID: {label_id} deleted successfully.")


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)
        label_handler = LabelHandler(service)

        label_name = "Example Label"
        label_id = label_handler.get_label_id(label_name)
        if label_id:
            delete_label(service, label_id)
        else:
            print(f'Label "{label_name}" not found.')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
