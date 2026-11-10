from googleapiclient.errors import HttpError

from google_api import get_gmail_service, get_label_handler, get_message_handler


def main():
    try:
        service = get_gmail_service()
        message_handler = get_message_handler(service=service)
        label_handler = get_label_handler(service=service)

        msg_id = next(message_handler.iter_messages(), None)
        if not msg_id:
            print("No messages found.")
            return

        label_name = "TEST_LABEL"
        label_id = label_handler.get_label_id(label_name)
        if label_id:
            label_handler.remove_label_from_message(msg_id, label_id)
            print(f"Removed label {label_name} from message {msg_id}")
        else:
            print(f"Label {label_name} not found.")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
