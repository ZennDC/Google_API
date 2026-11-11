import unittest
from unittest.mock import MagicMock

import httplib2
from googleapiclient.errors import HttpError

from google_api.gmail.objects import Message
from google_api.tools import GoogleAPITools


def _http_error(status: int, reason: str = "API error") -> HttpError:
    resp = httplib2.Response({"status": str(status), "reason": reason})
    return HttpError(resp=resp, content=reason.encode("utf-8"))


class TestGmailTools(unittest.TestCase):
    def setUp(self) -> None:
        self.msg_handler = MagicMock()
        self.label_handler = MagicMock()
        self.event_handler = MagicMock()
        self.calendar_handler = MagicMock()
        self.tools = GoogleAPITools(
            message_handler=self.msg_handler,
            label_handler=self.label_handler,
            event_handler=self.event_handler,
            calendar_handler=self.calendar_handler,
        )

    def test_list_emails_atomic_lookup_and_pruned_payload(self) -> None:
        self.msg_handler.get_messages.return_value = ["m1", "m2"]
        self.msg_handler.get_message.side_effect = [
            Message(
                id="m1",
                thread_id="t1",
                label_ids=["INBOX", "UNREAD"],
                snippet="Hi there &amp; welcome &#39;user&#39;",
                internal_date=1700000000000,
                sender="alice@example.com",
                subject="Welcome",
                raw_payload={"headers": [{"name": "X-Extra", "value": "bloat"}]},
            ),
            Message(
                id="m2",
                thread_id="t2",
                label_ids=["INBOX"],
                snippet="x" * 250,
                internal_date=0,
                sender=None,
                subject=None,
            ),
        ]

        res = self.tools.gmail.list_emails(
            query="from:alice", max_results=200, unread_only=True
        )

        self.assertTrue(res["success"])
        self.msg_handler.get_messages.assert_called_once_with(
            query="is:unread from:alice", max_results=50
        )
        self.assertEqual(res["data"]["count"], 2)

        first = res["data"]["emails"][0]
        self.assertEqual(first["id"], "m1")
        self.assertEqual(first["thread_id"], "t1")
        self.assertEqual(first["subject"], "Welcome")
        self.assertEqual(first["sender"], "alice@example.com")
        self.assertEqual(first["date"], "2023-11-14T22:13:20Z")
        self.assertTrue(first["unread"])
        self.assertEqual(first["snippet"], "Hi there & welcome 'user'")
        self.assertNotIn("raw_payload", first)

        second = res["data"]["emails"][1]
        self.assertEqual(second["subject"], "(No Subject)")
        self.assertFalse(second["unread"])
        self.assertTrue(second["snippet"].endswith("..."))
        self.assertEqual(len(second["snippet"]), 203)

    def test_read_email_strips_html_and_truncates(self) -> None:
        html_body = (
            "<html><head><style>body{color:red}</style></head>"
            "<body><script>alert(1)</script><p>Hello &amp; welcome!</p>"
            "<div>Line two</div></body></html>"
        )
        self.msg_handler.get_message.return_value = Message(
            id="m10",
            thread_id="t10",
            label_ids=["INBOX"],
            internal_date=1700000000000,
            sender="news@example.com",
            subject="Newsletter",
            body=html_body,
        )

        res = self.tools.gmail.read_email(email_id="m10", max_body_chars=18)

        self.assertTrue(res["success"])
        data = res["data"]
        self.assertTrue(data["truncated"])
        self.assertNotIn("<style>", data["body"])
        self.assertNotIn("alert(1)", data["body"])
        self.assertIn("Hello & welcome!", data["body"])
        self.assertTrue(data["body"].endswith("[... truncated]"))

    def test_read_email_preserves_plain_text_with_angle_brackets(self) -> None:
        self.msg_handler.get_message.return_value = Message(
            id="m11",
            thread_id="t11",
            label_ids=[],
            internal_date=1700000000000,
            sender="dev@example.com",
            subject="Math",
            body="Check that 2 < 3 and reply to <bob@example.com>.",
        )

        res = self.tools.gmail.read_email(email_id="m11")
        self.assertTrue(res["success"])
        self.assertFalse(res["data"]["truncated"])
        self.assertEqual(
            res["data"]["body"], "Check that 2 < 3 and reply to <bob@example.com>."
        )

    def test_read_email_validation_and_not_found(self) -> None:
        empty_res = self.tools.gmail.read_email(email_id="   ")
        self.assertFalse(empty_res["success"])
        self.assertEqual(empty_res["error_code"], "INVALID_INPUT")

        bad_len = self.tools.gmail.read_email(email_id="m1", max_body_chars=0)
        self.assertFalse(bad_len["success"])
        self.assertEqual(bad_len["error_code"], "INVALID_INPUT")

        self.msg_handler.get_message.side_effect = _http_error(404, "Not Found")
        not_found = self.tools.gmail.read_email(email_id="missing")
        self.assertFalse(not_found["success"])
        self.assertEqual(not_found["error_code"], "NOT_FOUND")

    def test_send_email_and_draft(self) -> None:
        self.msg_handler.send_message.return_value = {
            "id": "sent_1",
            "threadId": "thr_9",
            "labelIds": ["SENT"],
        }
        res = self.tools.gmail.send_email(
            to="alice@example.com, bob@example.com",
            subject="Sync",
            body="See you at 2pm",
            cc="carol@example.com",
            thread_id="thr_9",
        )
        self.assertTrue(res["success"])
        self.assertFalse(res["data"]["draft"])
        self.assertEqual(res["data"]["id"], "sent_1")
        self.msg_handler.send_message.assert_called_once_with(
            to=["alice@example.com", "bob@example.com"],
            subject="Sync",
            body="See you at 2pm",
            cc="carol@example.com",
            thread_id="thr_9",
        )

        self.msg_handler.create_draft.return_value = {
            "id": "draft_1",
            "message": {"id": "m_draft", "threadId": "thr_d"},
        }
        draft_res = self.tools.gmail.send_email(
            to="alice@example.com",
            subject="Draft",
            body="Pending review",
            save_as_draft=True,
        )
        self.assertTrue(draft_res["success"])
        self.assertTrue(draft_res["data"]["draft"])
        self.assertEqual(draft_res["data"]["id"], "draft_1")
        self.assertEqual(draft_res["data"]["thread_id"], "thr_d")

    def test_send_email_errors(self) -> None:
        empty_to = self.tools.gmail.send_email(to=" , ", subject="Hi", body="Body")
        self.assertFalse(empty_to["success"])
        self.assertEqual(empty_to["error_code"], "INVALID_INPUT")

        self.msg_handler.send_message.side_effect = _http_error(403, "Forbidden")
        perm = self.tools.gmail.send_email(to="a@b.com", subject="Hi", body="Body")
        self.assertFalse(perm["success"])
        self.assertEqual(perm["error_code"], "PERMISSION_DENIED")

    def test_apply_and_remove_label(self) -> None:
        # New label created & applied in one call
        self.label_handler.get_label_id.return_value = None
        self.label_handler.get_or_create_label_id.return_value = "Label_42"

        add_res = self.tools.gmail.apply_label(email_id="m1", label_name="Invoices")
        self.assertTrue(add_res["success"])
        self.assertEqual(add_res["data"]["label_id"], "Label_42")
        self.assertEqual(add_res["data"]["action"], "added")
        self.label_handler.add_label_to_message.assert_called_once_with(
            "m1", "Label_42"
        )

        # System label case-insensitive resolution
        self.label_handler.reset_mock()
        self.label_handler.get_label_id.side_effect = [None, "INBOX"]
        sys_res = self.tools.gmail.apply_label(email_id="m1", label_name="inbox")
        self.assertTrue(sys_res["success"])
        self.assertEqual(sys_res["data"]["label_id"], "INBOX")
        self.label_handler.get_or_create_label_id.assert_not_called()

        # Remove missing label returns NOT_FOUND without creating it
        self.label_handler.reset_mock()
        self.label_handler.get_label_id.side_effect = None
        self.label_handler.get_label_id.return_value = None
        rem_missing = self.tools.gmail.apply_label(
            email_id="m1", label_name="NonExistent", remove=True
        )
        self.assertFalse(rem_missing["success"])
        self.assertEqual(rem_missing["error_code"], "NOT_FOUND")

        # Remove existing label
        self.label_handler.get_label_id.return_value = "Label_42"
        rem_ok = self.tools.gmail.apply_label(
            email_id="m1", label_name="Invoices", remove=True
        )
        self.assertTrue(rem_ok["success"])
        self.assertEqual(rem_ok["data"]["action"], "removed")
        self.label_handler.remove_label_from_message.assert_called_once_with(
            "m1", "Label_42"
        )

    def test_trash_email_and_rate_limit(self) -> None:
        ok_res = self.tools.gmail.trash_email(email_id="m99")
        self.assertTrue(ok_res["success"])
        self.assertEqual(ok_res["data"]["id"], "m99")
        self.msg_handler.trash_message.assert_called_once_with("m99")

        self.msg_handler.trash_message.side_effect = _http_error(429, "Rate Limit")
        rate_res = self.tools.gmail.trash_email(email_id="m99")
        self.assertFalse(rate_res["success"])
        self.assertEqual(rate_res["error_code"], "RATE_LIMITED")


if __name__ == "__main__":
    unittest.main()
