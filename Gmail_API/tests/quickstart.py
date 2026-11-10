from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    """Shows basic usage of the Gmail API by listing the user's Gmail labels."""
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)

        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            print("No labels found.")
            return

        print("Labels:")
        for label in labels:
            print(f"- {label['name']}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
