class Label:
    def __init__(self, name: str, message_list_visibility: str = "", label_list_visibility: str = "", color: tuple = ("", "")):
        self.name = name
        self.message_list_visibility = message_list_visibility
        self.label_list_visibility = label_list_visibility
        self.color = color

        self._id = ""
        self._type = ""
        self._messages_total = ""
        self._messages_unread = ""
        self._threads_total = ""
        self._threads_unread = ""
        
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name):
        self._name = str(name)

    @property
    def message_list_visibility(self) -> str:
        return self._message_list_visibility

    @message_list_visibility.setter
    def message_list_visibility(self, visibility: str) -> None:
        if visibility not in ("show", "hide", ""):
            raise ValueError("Invalid visibility value")
        self._message_list_visibility = visibility

    @property
    def label_list_visibility(self) -> str:
        return self._label_list_visibility

    @label_list_visibility.setter
    def label_list_visibility(self, visibility: str) -> None:
        if visibility not in ("labelShow", "labelShowIfUnread", "labelHide", ""):
            raise ValueError("Invalid visibility value")
        self._message_list_visibility = visibility

    @property
    def color(self):
        return (self._text_color, self._background_color)

    @color.setter
    def color(self, value):
        """Takes a tuple: (text_color, background_color) as value."""
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("Color must be a tuple of (text_color, background_color).")
        self._text_color = value[0]
        self._background_color = value[1]

    @classmethod
    def from_json(cls, json_obj: dict) -> 'Label':
        obj = cls(
            name = json_obj['name'], 
            message_list_visibility = json_obj["messageListVisibility"],
            label_list_visibility = json_obj["labelListVisibility"],
            color = json_obj["color"],
        )
        obj._id = json_obj["id"]
        obj._type = json_obj["type"]
        obj._messages_total = json_obj["messagesTotal"]
        obj._messages_unread = json_obj["messagesUnread"]
        obj._threads_total = json_obj["threadsTotal"]
        obj._threads_unread = json_obj["threadsUnread"]

        return obj
        
    def build(self) -> dict:
        label_obj = {
            "name": self._name
        }

        if self.message_list_visibility:
            label_obj["messageListVisibility"] = self.message_list_visibility
        if self.label_list_visibility:
            label_obj["labelListVisibility"] = self.label_list_visibility
        if self.color:
            label_obj["color"] = {
                "textColor": self.color[0],
                "backgroundColor": self.color[1]
            }
