import base64
import email.utils
import logging
from collections.abc import Iterator

from googleapiclient.errors import HttpError

from .objects import Message

logger = logging.getLogger("google_api")


def _extract_text_body(payload: dict) -> str | None:
    """Recursively traverses payload parts preferring text/plain, falling back to text/html."""
    plain_text = None
    html_text = None

    def _traverse(part: dict):
        nonlocal plain_text, html_text
        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")

        if mime_type == "text/plain" and data and plain_text is None:
            plain_text = base64.urlsafe_b64decode(data.encode("ASCII")).decode(
                "utf-8", errors="replace"
            )
        elif mime_type == "text/html" and data and html_text is None:
            html_text = base64.urlsafe_b64decode(data.encode("ASCII")).decode(
                "utf-8", errors="replace"
            )

        for subpart in part.get("parts", []):
            _traverse(subpart)

    _traverse(payload)
    return plain_text if plain_text is not None else html_text


class MessageHandler:
    """A message handler for the gmail api."""

    def __init__(self, service, include_spam_trash: bool = False) -> None:
        self.service = service
        self.include_spam_trash = include_spam_trash

    def iter_messages(
        self, query: str | None = None, max_results: int | None = None
    ) -> Iterator[str]:
        """Generator yielding message IDs directly from the Gmail API with automatic pagination."""
        page_token = None
        count = 0

        while True:
            params = {
                "userId": "me",
                "pageToken": page_token,
                "includeSpamTrash": self.include_spam_trash,
            }
            if query:
                params["q"] = query

            response = self.service.users().messages().list(**params).execute()
            messages = response.get("messages", [])
            if not messages:
                break

            for msg in messages:
                yield msg["id"]
                count += 1
                if max_results and count >= max_results:
                    return

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def __iter__(self) -> Iterator[str]:
        """Allows iterating directly over MessageHandler instances: `for msg_id in handler:`"""
        return self.iter_messages()

    def get_messages(
        self, query: str | None = None, max_results: int | None = None
    ) -> list[str]:
        """Returns message IDs matching the optional query up to max_results."""
        return list(self.iter_messages(query=query, max_results=max_results))

    def trash_message(self, msg_id: str) -> None:
        """Moves the message with the specified ID to trash."""
        try:
            self.service.users().messages().trash(userId="me", id=msg_id).execute()
            logger.info(f"Trashed message with ID: {msg_id}")
        except HttpError as error:
            logger.error(f"Failed to trash message {msg_id}: {error}")
            raise

    def untrash_message(self, msg_id: str) -> None:
        """Restores the message with the specified ID from trash."""
        try:
            self.service.users().messages().untrash(userId="me", id=msg_id).execute()
            logger.info(f"Untrashed message with ID: {msg_id}")
        except HttpError as error:
            logger.error(f"Failed to untrash message {msg_id}: {error}")
            raise

    def get_message(self, msg_id: str, format: str = "metadata") -> Message:
        """Fetches a message by ID and returns a structured Message object.

        Allows fetching metadata (sender, subject, internal date) in a single API call,
        avoiding N+1 roundtrips.
        """
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format=format)
            .execute()
        )
        msg_obj = Message.from_json(raw)
        if format in ("full", "raw") and msg_obj.body is None:
            msg_obj.body = _extract_text_body(raw.get("payload", {}))
        return msg_obj

    def get_message_timestamp(self, msg_id: str) -> int:
        """Returns the received timestamp of the message based on id (milliseconds since Unix epoch)."""
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="minimal")
            .execute()
        )
        return int(message["internalDate"])

    def get_sender_address(self, msg_id: str) -> str | None:
        """Returns the email address of the sender."""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata")
            .execute()
        )
        for header in msg.get("payload", {}).get("headers", []):
            if header.get("name", "").lower() == "from":
                raw_sender = header.get("value", "")
                parsed = email.utils.parseaddr(raw_sender)[1]
                return parsed if parsed else (raw_sender or None)
        return None

    def get_subject(self, msg_id: str) -> str | None:
        """Returns the subject of the message based on id."""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata")
            .execute()
        )
        for header in msg.get("payload", {}).get("headers", []):
            if header.get("name", "").lower() == "subject":
                return header.get("value")
        return None

    def search_by_senders(
        self, senders: list[str] | str, max_results: int | None = None
    ) -> list[str]:
        """Retrieves message IDs from specified senders via a single server-side query."""
        if isinstance(senders, str):
            senders = [senders]
        query = " OR ".join(f"from:{sender}" for sender in senders)
        return list(self.iter_messages(query=query, max_results=max_results))

    def search_by_keywords(
        self, keywords: list[str] | str, max_results: int | None = None
    ) -> list[str]:
        """Retrieves message IDs matching subject keywords via a single server-side query."""
        if isinstance(keywords, str):
            keywords = [keywords]
        query = " OR ".join(f"subject:{kw}" for kw in keywords)
        return list(self.iter_messages(query=query, max_results=max_results))

    def get_message_body(self, msg_id: str) -> str:
        """Extracts the decoded body of the message with specified id, traversing multipart recursively."""
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )

        body = _extract_text_body(message.get("payload", {}))
        return body if body is not None else "No plain text or HTML content found."


class LabelHandler:
    """A label handler for the gmail api."""

    def __init__(self, service) -> None:
        self.service = service

    def label_exists(self, label_name: str) -> bool:
        """Check if a label already exists."""
        return self.get_label_id(label_name) is not None

    def create_label(self, label_name: str) -> dict:
        """Create a new label."""
        label = {"name": label_name}
        created = (
            self.service.users().labels().create(userId="me", body=label).execute()
        )
        logger.info(f'Label "{label_name}" created successfully.')
        return created

    def get_label_id(self, label_name: str) -> str | None:
        """Get the id of a label in the user's mailbox."""
        results = self.service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        if not labels:
            logger.debug("No labels found.")
            return None
        for label in labels:
            if label.get("name") == label_name:
                return label.get("id")

        logger.debug(f"Label {label_name} does not exist.")
        return None

    def add_label_to_message(self, msg_id: str, label_id: str) -> dict:
        """Adds the label to the message with the specified id"""
        body = {"addLabelIds": [label_id]}
        result = (
            self.service.users()
            .messages()
            .modify(userId="me", id=msg_id, body=body)
            .execute()
        )
        logger.info(f"Message with ID {msg_id} successfully labeled.")
        return result

    def get_or_create_label_id(self, label: str) -> str:
        """Returns the ID of an existing label, or creates it and returns the new ID in minimal API calls."""
        existing_id = self.get_label_id(label)
        if existing_id:
            logger.debug(f'Label "{label}" already exists.')
            return existing_id

        logger.info(f'Creating label "{label}".')
        created = self.create_label(label)
        created_id = created.get("id")
        if not created_id:
            raise RuntimeError(f"ID for newly created label {label} not found")
        return created_id

