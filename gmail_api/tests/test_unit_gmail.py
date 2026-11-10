import base64
import unittest
from unittest.mock import MagicMock

from gmail_api.handlers import LabelHandler, MessageHandler, _extract_text_body
from gmail_api.objects import Label, Message


class TestGmailObjects(unittest.TestCase):
    def test_label_build(self):
        label = Label(
            name="Invoices",
            message_list_visibility="show",
            label_list_visibility="labelShow",
            color=("#FFFFFF", "#000000"),
        )
        built = label.build()
        self.assertEqual(built["name"], "Invoices")
        self.assertEqual(built["messageListVisibility"], "show")
        self.assertEqual(built["labelListVisibility"], "labelShow")
        self.assertEqual(built["color"]["textColor"], "#FFFFFF")
        self.assertEqual(built["color"]["backgroundColor"], "#000000")

    def test_label_validation(self):
        label = Label(name="Test")
        with self.assertRaises(ValueError):
            label.message_list_visibility = "invalid_value"
        with self.assertRaises(ValueError):
            label.color = "not-a-tuple"

    def test_label_from_json_safely_handles_missing_keys(self):
        system_label_json = {
            "id": "INBOX",
            "name": "INBOX",
            "type": "system",
            "messagesTotal": 42,
            "messagesUnread": 5,
            "threadsTotal": 20,
            "threadsUnread": 2,
        }
        label = Label.from_json(system_label_json)
        self.assertEqual(label.id, "INBOX")
        self.assertEqual(label.name, "INBOX")
        self.assertEqual(label.messages_total, 42)
        self.assertEqual(label.color, ("", ""))
        self.assertEqual(label.message_list_visibility, "")

    def test_message_from_json(self):
        sample_json = {
            "id": "msg123",
            "threadId": "thr456",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Hello there...",
            "internalDate": "1672531199000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sender Name <sender@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
                ]
            },
        }
        msg = Message.from_json(sample_json)
        self.assertEqual(msg.id, "msg123")
        self.assertEqual(msg.thread_id, "thr456")
        self.assertEqual(msg.internal_date, 1672531199000)
        self.assertEqual(msg.sender, "sender@example.com")
        self.assertEqual(msg.subject, "Test Subject")


class TestGmailHandlers(unittest.TestCase):
    def test_get_or_create_label_id_existing(self):
        mock_service = MagicMock()
        mock_service.users().labels().list(userId="me").execute.return_value = {
            "labels": [{"id": "Label_1", "name": "Work"}]
        }
        handler = LabelHandler(mock_service)
        label_id = handler.get_or_create_label_id("Work")
        self.assertEqual(label_id, "Label_1")
        mock_service.users().labels().create.assert_not_called()

    def test_get_or_create_label_id_create_new(self):
        mock_service = MagicMock()
        labels_mock = mock_service.users.return_value.labels.return_value
        labels_mock.list.return_value.execute.return_value = {"labels": []}
        labels_mock.create.return_value.execute.return_value = {
            "id": "Label_New",
            "name": "NewProject",
        }

        handler = LabelHandler(mock_service)
        label_id = handler.get_or_create_label_id("NewProject")
        self.assertEqual(label_id, "Label_New")
        labels_mock.create.assert_called_once_with(
            userId="me", body={"name": "NewProject"}
        )

    def test_sender_parsing_with_parseaddr(self):
        mock_service = MagicMock()
        mock_service.users().messages().get(
            userId="me", id="msg1", format="metadata"
        ).execute.return_value = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "John Doe <johndoe@example.com>"}
                ]
            }
        }
        handler = MessageHandler(mock_service)
        self.assertEqual(handler.get_sender_address("msg1"), "johndoe@example.com")

        # Test bare email
        mock_service.users().messages().get(
            userId="me", id="msg2", format="metadata"
        ).execute.return_value = {
            "payload": {"headers": [{"name": "From", "value": "bare@example.com"}]}
        }
        self.assertEqual(handler.get_sender_address("msg2"), "bare@example.com")

    def test_extract_text_body_nested_multipart(self):
        plain_bytes = base64.urlsafe_b64encode(b"Plain text body").decode("ASCII")
        html_bytes = base64.urlsafe_b64encode(b"<p>HTML body</p>").decode("ASCII")

        nested_payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/html",
                            "body": {"data": html_bytes},
                        },
                        {
                            "mimeType": "text/plain",
                            "body": {"data": plain_bytes},
                        },
                    ],
                },
                {
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att1"},
                },
            ],
        }

        # text/plain preferred even if html appears first
        body = _extract_text_body(nested_payload)
        self.assertEqual(body, "Plain text body")


if __name__ == "__main__":
    unittest.main()

