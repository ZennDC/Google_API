from googleapiclient.errors import HttpError

from google_api import get_message_handler


def main():
    try:
        handler = get_message_handler()

        msg_id = next(handler.iter_messages(), None)
        if not msg_id:
            print("No messages found.")
            return

        sender_email = handler.get_sender_address(msg_id)
        subject = handler.get_subject(msg_id)
        print(f"Message ID: {msg_id}")
        print(f"Sender: {sender_email}")
        print(f"Subject: {subject}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
