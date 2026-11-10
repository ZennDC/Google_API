import base64

from googleapiclient.errors import HttpError

from ..logging_config import logger


class MessageHandler:
    """A message handler for the gmail api."""

    class _IdData:
        def __init__(self, includeSpamTrash=False) -> "MessageHandler._IdData":
            self.nextPageToken = None
            self.index = -1  # Start with -1 because we increment at the beginning
            self.messages = []
            self.includeSpamTrash = includeSpamTrash

    def __init__(self, service, includeSpamTrash=False) -> "MessageHandler":
        self.service = service
        self._id_data = self._IdData(includeSpamTrash)

    def getNextId(self) -> str:
        """Returns the id of last received mail the first time the function is called,
        otherwise it returns the id of the mail received before the previously returned mail's id
        """
        if not self._id_data.messages or self._id_data.index + 1 >= len(
            self._id_data.messages
        ):
            if self._id_data.nextPageToken is None and self._id_data.index != -1:
                return None
            response = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    pageToken=self._id_data.nextPageToken,
                    includeSpamTrash=self._id_data.includeSpamTrash,
                )
                .execute()
            )
            self._id_data.nextPageToken = response.get("nextPageToken")
            new_messages = response.get("messages", [])
            if not new_messages:
                return None
            self._id_data.messages.extend(new_messages)
            self._id_data.index += 1
            return self._id_data.messages[self._id_data.index]["id"]
        else:
            self._id_data.index += 1
            return self._id_data.messages[self._id_data.index]["id"]

    def resetIdData(self) -> None:
        """Resets the getNextId function to start at the newest message"""
        self._id_data.nextPageToken = None
        self._id_data.index = -1
        self._id_data.messages = []
        return self

    def trashMessage(self, msg_id: str) -> None:
        """Deletes the message with the specified id"""
        try:
            self.service.users().messages().trash(userId="me", id=msg_id).execute()
        except HttpError as error:
            logger.error(f"Failed to trash message {msg_id}: {error}")
            raise

    def untrashMessage(self, msg_id: str) -> None:
        """Undeletes the message with the specified id"""
        try:
            self.service.users().messages().untrash(userId="me", id=msg_id).execute()
            logger.info(f"Untrashed message with ID: {msg_id}")
        except HttpError as error:
            logger.error(f"Failed to untrash message {msg_id}: {error}")
            raise

    def getMessageTimestamp(self, msg_id: str) -> int:
        """Returns the received timestamp of the message based on id"""
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="minimal")
            .execute()
        )
        return int(message["internalDate"])

    def getSenderMailAddress(self, msg_id: str) -> str:
        """Returns the mail adress of the sender"""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata")
            .execute()
        )
        mail = None
        for header in msg["payload"]["headers"]:
            if header["name"] == "From":
                sender = header["value"]
                start_idx = sender.find("<")
                end_idx = sender.find(">", start_idx)
                if start_idx != -1 and end_idx != -1:
                    mail = sender[start_idx + 1 : end_idx]
                elif start_idx == end_idx == -1:
                    mail = sender
        return mail

    def getSubject(self, msg_id: str) -> str:
        """Returns the subject of the message based on id"""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata")
            .execute()
        )
        subject = None
        for header in msg["payload"]["headers"]:
            if header["name"] == "Subject":
                subject = header["value"]
        return subject

    def filterOnSenders(
        self, message_ids: list, sender_mail_addresses: list | str
    ) -> list:
        """Returns a list of messages that are send by the specified sender mail adresses"""
        logger.debug(
            f"Filtering {len(message_ids)} message(s) on sender mail adresses..."
        )
        filtered_messages = []

        if isinstance(sender_mail_addresses, str):
            sender_mail_addresses = [sender_mail_addresses]

        for msg_id in message_ids:
            sender_mail = self.getSenderMailAddress(msg_id)
            if sender_mail in sender_mail_addresses:
                filtered_messages.append(msg_id)

        logger.debug(
            f"Filtering complete, result: {len(filtered_messages)} message(s)."
        )
        return filtered_messages

    def filterSendersMulti(
        self, message_ids: list, *sender_mail_addresses_args: list | str
    ) -> list[list[str]]:
        """Returns a list of messages that are send by the specified sender mail adresses"""
        logger.debug(
            f"Filtering {len(message_ids)} message(s) on sender mail adresses..."
        )
        filtered_messages = [[] for _ in range(len(sender_mail_addresses_args))]

        for sender_mail_addresses in sender_mail_addresses_args:
            if isinstance(sender_mail_addresses, str):
                sender_mail_addresses = [sender_mail_addresses]

        for msg_id in message_ids:
            try:
                sender_mail = self.getSenderMailAddress(msg_id)
                for index, sender_mail_addresses in enumerate(
                    sender_mail_addresses_args
                ):
                    if sender_mail in sender_mail_addresses:
                        filtered_messages[index].append(msg_id)
            except HttpError as error:
                logger.error(f"Error fetching sender for message {msg_id}: {error}")

        logger.debug(
            f"Filtering complete, result: {len(filtered_messages)} message(s)."
        )
        return filtered_messages

    def filterOnKeywords(self, message_ids: list, keywords: list[str]) -> list:
        """Filters the subjects of the messages with the provided ids on keywords."""
        logger.debug(f"Filtering {len(message_ids)} message(s) on keywords...")
        filtered = []

        for msg_id in message_ids:
            try:
                subject = self.getSubject(msg_id)
                for keyword in keywords:
                    if subject and keyword in subject.lower():
                        filtered.append(msg_id)
                        break
            except HttpError as error:
                logger.error(f"Error reading subject for message {msg_id}: {error}")

        logger.debug(f"Filtering complete, result: {len(filtered)} message(s).")
        return filtered

    def getMessageBody(self, msg_id: str) -> str:
        """Extracts the body of the message with specified id."""
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )

        if "parts" in message["payload"]:
            for part in message["payload"]["parts"]:
                if part["mimeType"] in ("text/plain", "text/html"):
                    body = part["body"]["data"]
                    return base64.urlsafe_b64decode(body.encode("ASCII")).decode(
                        "utf-8"
                    )
        else:
            body = message["payload"]["body"]["data"]
            return base64.urlsafe_b64decode(body.encode("ASCII")).decode("utf-8")
        return "No plain text or HTML content found."


class LabelHandler:
    """A label handler for the gmail api."""

    def __init__(self, service) -> "LabelHandler":
        self.service = service

    def label_exists(self, label_name: str) -> bool:
        """Check if a label already exists."""
        labels = (
            self.service.users().labels().list(userId="me").execute().get("labels", [])
        )
        return any(label["name"] == label_name for label in labels)

    def create_label(self, label_name: str) -> None:
        """Create a new label."""
        label = {"name": label_name}
        self.service.users().labels().create(userId="me", body=label).execute()
        logger.info(f'Label "{label_name}" created successfully.')

    def get_label_id(self, label_name: str) -> str | None:
        """Get the id of a label in the user's mailbox."""
        results = self.service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        if not labels:
            logger.debug("No labels found.")
            return None
        for label in labels:
            if label["name"] == label_name:
                return label["id"]

        logger.debug(f"Label {label_name} does not exist.")
        return None

    def add_label_to_message(self, msg_id: str, label_id: str) -> None:
        """Adds the label to the message with the specified id"""
        body = {"addLabelIds": [label_id]}
        self.service.users().messages().modify(
            userId="me", id=msg_id, body=body
        ).execute()
        logger.info(f"Message with ID {msg_id} successfully labeled.")

    def get_or_create_label_id(self, label: str) -> str:
        if not self.label_exists(label):
            logger.info(f'Creating label "{label}".')
            self.create_label(label)
        else:
            logger.debug(f'Label "{label}" already exists.')

        id = self.get_label_id(label)
        if not id:
            raise RuntimeError(f"ID for {label} not found")

        return id
