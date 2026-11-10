from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_api.handlers import LabelHandler, MessageHandler
from oauth import get_credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)
        message_handler = MessageHandler(service)
        label_handler = LabelHandler(service)

        label_name = "SenderTestLabel"
        label_id = label_handler.get_or_create_label_id(label_name)

        msg_id = next(message_handler.iter_messages(), None)
        if not msg_id:
            print("No messages found.")
            return

        sender = message_handler.get_sender_address(msg_id)
        print(f"Applying label '{label_name}' to message from: {sender}")
        label_handler.add_label_to_message(msg_id, label_id)
        print("Done.")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
