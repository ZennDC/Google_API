from googleapiclient.errors import HttpError

from google_api import get_label_handler


def main():
    try:
        label_handler = get_label_handler()
        service = label_handler.service

        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            print("No labels found.")
        else:
            print("Labels:")
            for label in labels:
                exists = label_handler.label_exists(label["name"])
                print(f"{label['name']} - {label['id']} (verified: {exists})")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
