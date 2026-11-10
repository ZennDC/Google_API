from googleapiclient.errors import HttpError

from google_api import get_message_handler


def main():
    try:
        handler = get_message_handler()

        print("Fetching first 10 message IDs using MessageHandler pagination...")
        for i in range(1, 11):
            msg_id = next(handler.iter_messages(), None)
            if not msg_id:
                print(f"No more messages found after {i - 1} messages.")
                break
            print(f"{i}: {msg_id}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
