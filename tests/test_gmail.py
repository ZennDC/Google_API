import base64
import unittest
from unittest.mock import MagicMock

import httplib2
from googleapiclient.errors import HttpError

from google_api.gmail.handlers import (
    LabelHandler,
    MessageHandler,
    _extract_text_body,
)
from google_api.gmail.objects import Label, Message


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
            label.label_list_visibility = "invalid_visibility"
        with self.assertRaises(ValueError):
            label.color = "not-a-tuple"
        with self.assertRaises(ValueError):
            label.color = ("#FFF",)

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

    def test_label_from_json_with_color_dict(self):
        custom_json = {
            "id": "Label_1",
            "name": "Personal",
            "messageListVisibility": "hide",
            "labelListVisibility": "labelHide",
            "color": {"textColor": "#111111", "backgroundColor": "#eeeeee"},
        }
        label = Label.from_json(custom_json)
        self.assertEqual(label.color, ("#111111", "#eeeeee"))
        self.assertEqual(label.message_list_visibility, "hide")
        self.assertEqual(label.label_list_visibility, "labelHide")

    def test_message_from_json_and_headers(self):
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
        self.assertEqual(msg.snippet, "Hello there...")
        self.assertEqual(msg.label_ids, ["INBOX", "UNREAD"])


class TestGmailHandlers(unittest.TestCase):
    def test_iter_messages_pagination_and_max_results(self):
        mock_service = MagicMock()
        mock_list = mock_service.users().messages().list

        # Page 1 returns 2 messages with a nextPageToken
        # Page 2 returns 2 messages without nextPageToken
        mock_list.return_value.execute.side_effect = [
            {"messages": [{"id": "m1"}, {"id": "m2"}], "nextPageToken": "token2"},
            {"messages": [{"id": "m3"}, {"id": "m4"}], "nextPageToken": None},
        ]

        handler = MessageHandler(mock_service)
        all_ids = list(handler.iter_messages())
        self.assertEqual(all_ids, ["m1", "m2", "m3", "m4"])

        # Test __iter__ and get_messages
        mock_list.return_value.execute.side_effect = [
            {"messages": [{"id": "m1"}], "nextPageToken": None}
        ]
        self.assertEqual(list(handler), ["m1"])

        mock_list.return_value.execute.side_effect = [
            {"messages": [{"id": "m2"}], "nextPageToken": None}
        ]
        self.assertEqual(handler.get_messages(), ["m2"])

        # Test max_results capping
        mock_list.return_value.execute.side_effect = [
            {"messages": [{"id": "m1"}, {"id": "m2"}], "nextPageToken": "token2"},
            {"messages": [{"id": "m3"}, {"id": "m4"}], "nextPageToken": None},
        ]
        capped_ids = list(handler.iter_messages(max_results=3))
        self.assertEqual(capped_ids, ["m1", "m2", "m3"])

    def test_search_queries(self):
        mock_service = MagicMock()
        mock_list = mock_service.users().messages().list
        mock_list.return_value.execute.return_value = {
            "messages": [{"id": "m1"}],
            "nextPageToken": None,
        }

        handler = MessageHandler(mock_service)
        handler.search_by_senders(["test@example.com", "other@example.com"])
        mock_list.assert_called_with(
            userId="me",
            pageToken=None,
            includeSpamTrash=False,
            q="from:test@example.com OR from:other@example.com",
        )

        handler.search_by_keywords(["urgent", "action required"])
        mock_list.assert_called_with(
            userId="me",
            pageToken=None,
            includeSpamTrash=False,
            q="subject:urgent OR subject:action required",
        )

        # Single string queries
        handler.search_by_senders("single@example.com")
        handler.search_by_keywords("singlekeyword")

    def test_trash_and_untrash_message(self):
        mock_service = MagicMock()
        handler = MessageHandler(mock_service)

        handler.trash_message("msg123")
        mock_service.users().messages().trash.assert_called_once_with(
            userId="me", id="msg123"
        )

        handler.untrash_message("msg123")
        mock_service.users().messages().untrash.assert_called_once_with(
            userId="me", id="msg123"
        )

    def test_trash_untrash_http_error(self):
        mock_service = MagicMock()
        resp = httplib2.Response({"status": 404, "reason": "Not Found"})
        mock_service.users().messages().trash().execute.side_effect = HttpError(
            resp, b"Message not found"
        )
        mock_service.users().messages().untrash().execute.side_effect = HttpError(
            resp, b"Message not found"
        )

        handler = MessageHandler(mock_service)
        with self.assertRaises(HttpError):
            handler.trash_message("bad_id")

        with self.assertRaises(HttpError):
            handler.untrash_message("bad_id")

    def test_get_message_structured(self):
        mock_service = MagicMock()
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_full",
            "threadId": "thr_full",
            "internalDate": "1672531199000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice <alice@example.com>"},
                    {"name": "Subject", "value": "Status Report"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Body text").decode("ASCII")
                },
            },
        }

        handler = MessageHandler(mock_service)
        msg = handler.get_message("msg_full", format="full")
        self.assertEqual(msg.id, "msg_full")
        self.assertEqual(msg.sender, "alice@example.com")
        self.assertEqual(msg.body, "Body text")

    def test_get_message_metadata_and_timestamp(self):
        mock_service = MagicMock()

        def mock_get(userId, id, format):
            mock_call = MagicMock()
            if format == "minimal":
                mock_call.execute.return_value = {"internalDate": "1672531199000"}
            elif format == "metadata":
                mock_call.execute.return_value = {
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Meeting notes"},
                            {"name": "From", "value": "Boss <boss@example.com>"},
                        ]
                    }
                }
            return mock_call

        mock_service.users().messages().get.side_effect = mock_get

        handler = MessageHandler(mock_service)
        self.assertEqual(handler.get_message_timestamp("msg1"), 1672531199000)
        self.assertEqual(handler.get_subject("msg1"), "Meeting notes")
        self.assertEqual(handler.get_sender_address("msg1"), "boss@example.com")

    def test_get_message_body_and_fallback(self):
        mock_service = MagicMock()
        mock_service.users().messages().get().execute.return_value = {
            "payload": {
                "mimeType": "application/pdf",
                "body": {},
            }
        }
        handler = MessageHandler(mock_service)
        self.assertEqual(
            handler.get_message_body("msg_pdf"), "No plain text or HTML content found."
        )

    def test_label_operations(self):
        mock_service = MagicMock()
        labels_mock = mock_service.users().labels()
        labels_mock.list().execute.return_value = {
            "labels": [{"id": "Label_1", "name": "Work"}]
        }

        handler = LabelHandler(mock_service)
        self.assertTrue(handler.label_exists("Work"))
        self.assertFalse(handler.label_exists("NonExistent"))
        self.assertEqual(handler.get_label_id("Work"), "Label_1")
        self.assertIsNone(handler.get_label_id("NonExistent"))

        # Empty labels list
        labels_mock.list().execute.return_value = {"labels": []}
        self.assertIsNone(handler.get_label_id("Any"))

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

    def test_get_or_create_label_id_missing_id_raises(self):
        mock_service = MagicMock()
        labels_mock = mock_service.users.return_value.labels.return_value
        labels_mock.list.return_value.execute.return_value = {"labels": []}
        labels_mock.create.return_value.execute.return_value = {"name": "NoId"}

        handler = LabelHandler(mock_service)
        with self.assertRaises(RuntimeError):
            handler.get_or_create_label_id("NoId")

    def test_add_label_to_message(self):
        mock_service = MagicMock()
        handler = LabelHandler(mock_service)
        handler.add_label_to_message("msg123", "Label_1")
        mock_service.users().messages().modify.assert_called_once_with(
            userId="me", id="msg123", body={"addLabelIds": ["Label_1"]}
        )

    def test_remove_label_from_message(self):
        mock_service = MagicMock()
        mock_modify = mock_service.users().messages().modify
        mock_modify.return_value.execute.return_value = {"id": "msg123", "labelIds": []}
        handler = LabelHandler(mock_service)
        result = handler.remove_label_from_message("msg123", "Label_1")
        self.assertEqual(result, {"id": "msg123", "labelIds": []})
        mock_modify.assert_called_once_with(
            userId="me", id="msg123", body={"removeLabelIds": ["Label_1"]}
        )

    def test_delete_label(self):
        mock_service = MagicMock()
        mock_delete = mock_service.users().labels().delete
        handler = LabelHandler(mock_service)
        handler.delete_label("Label_1")
        mock_delete.assert_called_once_with(userId="me", id="Label_1")

    def test_update_label_with_name_only(self):
        mock_service = MagicMock()
        mock_patch = mock_service.users().labels().patch
        mock_patch.return_value.execute.return_value = {
            "id": "Label_1",
            "name": "Renamed",
        }
        handler = LabelHandler(mock_service)
        result = handler.update_label("Label_1", name="Renamed")
        self.assertEqual(result, {"id": "Label_1", "name": "Renamed"})
        mock_patch.assert_called_once_with(
            userId="me", id="Label_1", body={"name": "Renamed"}
        )

    def test_update_label_with_label_object(self):
        mock_service = MagicMock()
        mock_patch = mock_service.users().labels().patch
        handler = LabelHandler(mock_service)
        label_obj = Label(
            name="NewWork",
            message_list_visibility="show",
            label_list_visibility="labelShow",
            color=("#FFFFFF", "#000000"),
        )
        handler.update_label("Label_1", label=label_obj)
        mock_patch.assert_called_once_with(
            userId="me",
            id="Label_1",
            body={
                "name": "NewWork",
                "messageListVisibility": "show",
                "labelListVisibility": "labelShow",
                "color": {"textColor": "#FFFFFF", "backgroundColor": "#000000"},
            },
        )

    def test_delete_message(self):
        mock_service = MagicMock()
        mock_delete = mock_service.users().messages().delete
        handler = MessageHandler(mock_service)
        handler.delete_message("msg123")
        mock_delete.assert_called_once_with(userId="me", id="msg123")

    def test_send_message_basic(self):
        mock_service = MagicMock()
        mock_send = mock_service.users().messages().send
        mock_send.return_value.execute.return_value = {"id": "msg_sent_1"}
        handler = MessageHandler(mock_service)
        result = handler.send_message(
            to="recipient@example.com",
            subject="Test Subject",
            body="Hello World",
            cc="cc@example.com",
            bcc=["bcc1@example.com", "bcc2@example.com"],
            thread_id="thread_999",
        )
        self.assertEqual(result, {"id": "msg_sent_1"})
        call_kwargs = mock_send.call_args[1]
        self.assertEqual(call_kwargs["userId"], "me")
        self.assertEqual(call_kwargs["body"]["threadId"], "thread_999")
        raw_b64 = call_kwargs["body"]["raw"]
        raw_bytes = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
        self.assertIn(b"To: recipient@example.com", raw_bytes)
        self.assertIn(b"Subject: Test Subject", raw_bytes)
        self.assertIn(b"Cc: cc@example.com", raw_bytes)
        self.assertIn(b"Bcc: bcc1@example.com, bcc2@example.com", raw_bytes)
        self.assertIn(b"Hello World", raw_bytes)

    def test_send_message_raw_bytes(self):
        mock_service = MagicMock()
        mock_send = mock_service.users().messages().send
        handler = MessageHandler(mock_service)
        handler.send_message(
            to=[], raw_message=b"From: a@b.com\r\nSubject: Hi\r\n\r\nTest"
        )
        call_kwargs = mock_send.call_args[1]
        self.assertEqual(
            call_kwargs["body"]["raw"],
            base64.urlsafe_b64encode(
                b"From: a@b.com\r\nSubject: Hi\r\n\r\nTest"
            ).decode("utf-8"),
        )

    def test_create_draft(self):
        mock_service = MagicMock()
        mock_create = mock_service.users().drafts().create
        mock_create.return_value.execute.return_value = {
            "id": "draft_1",
            "message": {"id": "msg_d1"},
        }
        handler = MessageHandler(mock_service)
        result = handler.create_draft(
            to=["to1@example.com", "to2@example.com"],
            subject="Draft Subject",
            body="Draft Body",
        )
        self.assertEqual(result["id"], "draft_1")
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["userId"], "me")
        raw_b64 = call_kwargs["body"]["message"]["raw"]
        raw_bytes = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
        self.assertIn(b"To: to1@example.com, to2@example.com", raw_bytes)
        self.assertIn(b"Draft Subject", raw_bytes)
        self.assertIn(b"Draft Body", raw_bytes)

    def test_batch_modify(self):
        mock_service = MagicMock()
        mock_batch_modify = mock_service.users().messages().batchModify
        handler = MessageHandler(mock_service)
        handler.batch_modify(
            ["m1", "m2", "m3"], add_label_ids=["Label_A"], remove_label_ids=["UNREAD"]
        )
        mock_batch_modify.assert_called_once_with(
            userId="me",
            body={
                "ids": ["m1", "m2", "m3"],
                "addLabelIds": ["Label_A"],
                "removeLabelIds": ["UNREAD"],
            },
        )

        # Empty list should no-op
        mock_batch_modify.reset_mock()
        handler.batch_modify([])
        mock_batch_modify.assert_not_called()

    def test_batch_delete(self):
        mock_service = MagicMock()
        mock_batch_delete = mock_service.users().messages().batchDelete
        handler = MessageHandler(mock_service)
        handler.batch_delete(["m1", "m2"])
        mock_batch_delete.assert_called_once_with(
            userId="me",
            body={"ids": ["m1", "m2"]},
        )

        # Empty list should no-op
        mock_batch_delete.reset_mock()
        handler.batch_delete([])
        mock_batch_delete.assert_not_called()

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

        body = _extract_text_body(nested_payload)
        self.assertEqual(body, "Plain text body")

    def test_context_managers_and_close(self):
        mock_service = MagicMock()
        mock_service.close = MagicMock()

        # MessageHandler context manager
        with MessageHandler(mock_service) as handler:
            self.assertIsInstance(handler, MessageHandler)
        mock_service.close.assert_called_once()

        mock_service.close.reset_mock()
        # LabelHandler context manager
        with LabelHandler(mock_service) as handler:
            self.assertIsInstance(handler, LabelHandler)
        mock_service.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
