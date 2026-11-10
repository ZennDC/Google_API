from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_api.handlers import LabelHandler, MessageHandler
from oauth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("gmail", "v1", credentials=creds)

        message_handler = MessageHandler(service)
        label_handler = LabelHandler(service)

        msg_id = message_handler.getNextId()
        if not msg_id:
            print("No messages found.")
            return

        label_name = "TEST_LABEL"
        label_id = label_handler.get_or_create_label_id(label_name)
        label_handler.add_label_to_message(msg_id, label_id)
        print(f"Added label {label_name} to message {msg_id}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
