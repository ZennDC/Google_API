from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Gmail_API.handlers import LabelHandler
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)

        label_handler = LabelHandler(service)
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            print("No labels found.")
        else:
            print("Labels:")
            for label in labels:
                exists = label_handler.label_exists(label["name"])
                print(f"{label['name']} - {label['id']} (verified: {exists})")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
