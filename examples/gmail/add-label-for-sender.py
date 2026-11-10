from googleapiclient.errors import HttpError

from google_api import get_gmail_service, get_label_handler, get_message_handler


def main():
    try:
        service = get_gmail_service()
        message_handler = get_message_handler(service=service)
        label_handler = get_label_handler(service=service)

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
