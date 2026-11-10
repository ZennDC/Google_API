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

        # Collect the last 5 messages
        message_ids = []
        for _ in range(5):
            mid = next(handler.iter_messages(), None)
            if mid:
                message_ids.append(mid)
            else:
                break

        if not message_ids:
            print("No messages to check.")
            return

        # Target sender to find
        first_sender = handler.get_sender_address(message_ids[0])
        print(f"Searching for messages from: {first_sender}")
        matching = handler.filterSenders(message_ids, [first_sender])
        print(f"Found {len(matching)} matching message(s): {matching}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
