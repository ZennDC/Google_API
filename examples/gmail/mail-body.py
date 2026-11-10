from googleapiclient.errors import HttpError

from google_api import get_message_handler


def main():
    try:
        handler = get_message_handler()

        msg_id = next(handler.iter_messages(), None)
        if not msg_id:
            print("No messages found.")
            return

        body = handler.get_message_body(msg_id)
        print(f"Message ID: {msg_id}")
        print("Body preview (first 200 chars):")
        print(body[:200] if body else "Empty body")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
