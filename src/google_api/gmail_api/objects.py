from dataclasses import dataclass, field


@dataclass
class Message:
    """Structured representation of a Gmail message with metadata and content."""

    id: str
    thread_id: str = ""
    label_ids: list[str] = field(default_factory=list)
    snippet: str = ""
    internal_date: int = 0
    sender: str | None = None
    subject: str | None = None
    body: str | None = None
    raw_payload: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, json_obj: dict) -> "Message":
        """Builds a Message object from a Gmail API messages.get response."""
        import email.utils

        msg_id = json_obj.get("id", "")
        thread_id = json_obj.get("threadId", "")
        label_ids = json_obj.get("labelIds", [])
        snippet = json_obj.get("snippet", "")
        internal_date = int(json_obj.get("internalDate", 0))

        payload = json_obj.get("payload", {})
        headers = payload.get("headers", [])

        sender = None
        subject = None
        for header in headers:
            name = header.get("name", "").lower()
            if name == "from":
                raw_sender = header.get("value", "")
                parsed = email.utils.parseaddr(raw_sender)[1]
                sender = parsed if parsed else (raw_sender or None)
            elif name == "subject":
                subject = header.get("value")

        return cls(
            id=msg_id,
            thread_id=thread_id,
            label_ids=label_ids,
            snippet=snippet,
            internal_date=internal_date,
            sender=sender,
            subject=subject,
            raw_payload=payload,
        )


@dataclass
class Label:
    """A label representation for the Gmail API."""

    name: str
    message_list_visibility: str = ""
    label_list_visibility: str = ""
    color: tuple[str, str] = field(default_factory=lambda: ("", ""))
    id: str = ""
    type: str = ""
    messages_total: int = 0
    messages_unread: int = 0
    threads_total: int = 0
    threads_unread: int = 0

    def __post_init__(self) -> None:
        self._validate_message_list_visibility(self.message_list_visibility)
        self._validate_label_list_visibility(self.label_list_visibility)
        self._validate_color(self.color)

    def _validate_message_list_visibility(self, visibility: str) -> None:
        if visibility not in ("show", "hide", ""):
            raise ValueError(f"Invalid message_list_visibility value: {visibility}")

    def _validate_label_list_visibility(self, visibility: str) -> None:
        if visibility not in ("labelShow", "labelShowIfUnread", "labelHide", ""):
            raise ValueError(f"Invalid label_list_visibility value: {visibility}")

    def _validate_color(self, color: tuple) -> None:
        if not isinstance(color, tuple) or len(color) != 2:
            raise ValueError("Color must be a tuple of (text_color, background_color).")

    def __setattr__(self, name: str, value: any) -> None:
        if name == "message_list_visibility":
            self._validate_message_list_visibility(value)
        elif name == "label_list_visibility":
            self._validate_label_list_visibility(value)
        elif name == "color":
            self._validate_color(value)
        super().__setattr__(name, value)

    @classmethod
    def from_json(cls, json_obj: dict) -> "Label":
        """Instantiates a Label from a Gmail API dictionary response safely."""
        color_dict = json_obj.get("color")
        if isinstance(color_dict, dict):
            color = (
                color_dict.get("textColor", ""),
                color_dict.get("backgroundColor", ""),
            )
        elif isinstance(color_dict, tuple) and len(color_dict) == 2:
            color = color_dict
        else:
            color = ("", "")

        return cls(
            name=json_obj.get("name", ""),
            message_list_visibility=json_obj.get("messageListVisibility", ""),
            label_list_visibility=json_obj.get("labelListVisibility", ""),
            color=color,
            id=json_obj.get("id", ""),
            type=json_obj.get("type", ""),
            messages_total=int(json_obj.get("messagesTotal", 0)),
            messages_unread=int(json_obj.get("messagesUnread", 0)),
            threads_total=int(json_obj.get("threadsTotal", 0)),
            threads_unread=int(json_obj.get("threadsUnread", 0)),
        )

    def build(self) -> dict:
        """Serializes the Label for Gmail API create/update requests."""
        label_obj = {"name": self.name}

        if self.message_list_visibility:
            label_obj["messageListVisibility"] = self.message_list_visibility
        if self.label_list_visibility:
            label_obj["labelListVisibility"] = self.label_list_visibility
        if self.color and (self.color[0] or self.color[1]):
            label_obj["color"] = {
                "textColor": self.color[0],
                "backgroundColor": self.color[1],
            }

        return label_obj
