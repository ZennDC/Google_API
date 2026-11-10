from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_api.handlers import MessageHandler
from oauth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)
        handler = MessageHandler(service)

        print("Fetching first 10 message IDs using MessageHandler pagination...")
        for i in range(1, 11):
            msg_id = handler.getNextId()
            if not msg_id:
                print(f"No more messages found after {i - 1} messages.")
                break
            print(f"{i}: {msg_id}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
