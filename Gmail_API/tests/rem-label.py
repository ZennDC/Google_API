from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Gmail_API.handlers import LabelHandler, MessageHandler
from OAuth import get_credentials

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
        label_id = label_handler.get_label_id(label_name)
        if label_id:
            body = {"removeLabelIds": [label_id]}
            service.users().messages().modify(
                userId="me", id=msg_id, body=body
            ).execute()
            print(f"Removed label {label_name} from message {msg_id}")
        else:
            print(f"Label {label_name} not found.")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
