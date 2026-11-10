from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Gmail_API.handlers import MessageHandler
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)
        handler = MessageHandler(service)

        msg_id = handler.getNextId()
        if not msg_id:
            print("No messages found.")
            return

        body = handler.getMessageBody(msg_id)
        print(f"Message ID: {msg_id}")
        print("Body preview (first 200 chars):")
        print(body[:200] if body else "Empty body")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
