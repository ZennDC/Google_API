from googleapiclient.errors import HttpError

from google_api import get_gmail_service


def main():
    """Shows basic usage of the Gmail API by listing the user's Gmail labels."""
    try:
        service = get_gmail_service()

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
