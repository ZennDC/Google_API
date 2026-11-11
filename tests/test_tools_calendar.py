import unittest
from unittest.mock import MagicMock

import httplib2
from googleapiclient.errors import HttpError

from google_api.calendar.objects import Event, TimedEvent
from google_api.tools import GoogleAPITools


def _http_error(status: int, reason: str = "API error") -> HttpError:
    resp = httplib2.Response({"status": str(status), "reason": reason})
    return HttpError(resp=resp, content=reason.encode("utf-8"))


class TestCalendarTools(unittest.TestCase):
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

    def test_schedule_timed_event_and_named_calendar_resolution(self) -> None:
        self.calendar_handler.find_calendar_id_by_name.return_value = (
            "work@group.calendar.google.com"
        )
        self.event_handler.plan_event.return_value = {
            "id": "evt_1",
            "summary": "Design Review",
            "start": {"dateTime": "2026-11-12T14:00:00+01:00"},
            "end": {"dateTime": "2026-11-12T15:00:00+01:00"},
            "htmlLink": "https://calendar.google.com/event?eid=1",
            "etag": '"raw-etag"',
            "iCalUID": "raw-uid",
        }

        res = self.tools.calendar.schedule_event(
            title="Design Review",
            start="2026-11-12T14:00",
            end="2026-11-12T15:00",
            location="Room A",
            attendees=["bob@example.com"],
            calendar_name="Work",
        )

        self.assertTrue(res["success"])
        self.calendar_handler.find_calendar_id_by_name.assert_called_once_with("Work")
        cal_id, event_arg = self.event_handler.plan_event.call_args.args
        self.assertEqual(cal_id, "work@group.calendar.google.com")
        self.assertIsInstance(event_arg, TimedEvent)
        self.assertEqual(event_arg.time_zone, "Europe/Brussels")

        data = res["data"]
        self.assertEqual(data["id"], "evt_1")
        self.assertEqual(data["title"], "Design Review")
        self.assertFalse(data["all_day"])
        self.assertNotIn("etag", data)
        self.assertNotIn("iCalUID", data)

    def test_schedule_all_day_single_day_bumps_exclusive_end_date(self) -> None:
        self.event_handler.plan_event.return_value = {
            "id": "evt_all_day",
            "summary": "Conference",
            "start": {"date": "2026-11-12"},
            "end": {"date": "2026-11-13"},
        }

        res = self.tools.calendar.schedule_event(
            title="Conference",
            start="2026-11-12",
            end="2026-11-12",
        )

        self.assertTrue(res["success"])
        self.assertTrue(res["data"]["all_day"])
        _, event_arg = self.event_handler.plan_event.call_args.args
        self.assertIsInstance(event_arg, Event)
        built = event_arg.build()
        self.assertEqual(built["start"]["date"], "2026-11-12")
        self.assertEqual(built["end"]["date"], "2026-11-13")

    def test_schedule_event_respects_overridden_default_timezone(self) -> None:
        custom_tools = GoogleAPITools(
            default_time_zone="America/New_York",
            message_handler=self.msg_handler,
            label_handler=self.label_handler,
            event_handler=self.event_handler,
            calendar_handler=self.calendar_handler,
        )
        self.event_handler.plan_event.return_value = {
            "id": "evt_ny",
            "summary": "Standup",
            "start": {"dateTime": "2026-11-12T09:00:00-05:00"},
            "end": {"dateTime": "2026-11-12T09:30:00-05:00"},
        }

        res = custom_tools.calendar.schedule_event(
            title="Standup",
            start="2026-11-12T09:00",
            end="2026-11-12T09:30",
        )
        self.assertTrue(res["success"])
        _, event_arg = self.event_handler.plan_event.call_args.args
        self.assertEqual(event_arg.time_zone, "America/New_York")

    def test_schedule_event_validation_and_missing_calendar(self) -> None:
        bad_range = self.tools.calendar.schedule_event(
            title="Meeting",
            start="2026-11-12T15:00",
            end="2026-11-12T14:00",
        )
        self.assertFalse(bad_range["success"])
        self.assertEqual(bad_range["error_code"], "INVALID_INPUT")

        mixed = self.tools.calendar.schedule_event(
            title="Meeting",
            start="2026-11-12",
            end="2026-11-12T14:00",
        )
        self.assertFalse(mixed["success"])
        self.assertEqual(mixed["error_code"], "INVALID_INPUT")

        bad_tz = self.tools.calendar.schedule_event(
            title="Meeting",
            start="2026-11-12T14:00",
            end="2026-11-12T15:00",
            time_zone="Bad/Zone",
        )
        self.assertFalse(bad_tz["success"])
        self.assertEqual(bad_tz["error_code"], "INVALID_INPUT")

        self.calendar_handler.find_calendar_id_by_name.return_value = None
        missing_cal = self.tools.calendar.schedule_event(
            title="Meeting",
            start="2026-11-12T14:00",
            end="2026-11-12T15:00",
            calendar_name="UnknownCal",
        )
        self.assertFalse(missing_cal["success"])
        self.assertEqual(missing_cal["error_code"], "NOT_FOUND")

    def test_list_events_pagination_and_pruned_output(self) -> None:
        mock_list = self.event_handler.service.events().list
        mock_list.return_value.execute.side_effect = [
            {
                "items": [
                    {
                        "id": "e1",
                        "summary": "Morning Coffee",
                        "start": {"dateTime": "2026-11-12T09:00:00+01:00"},
                        "end": {"dateTime": "2026-11-12T09:30:00+01:00"},
                        "location": "Cafe",
                        "attendees": [
                            {"email": "a@example.com", "responseStatus": "accepted"}
                        ],
                        "etag": '"bloat"',
                    }
                ],
                "nextPageToken": "page2",
            },
            {
                "items": [
                    {
                        "id": "e2",
                        "summary": "Holiday",
                        "start": {"date": "2026-11-13"},
                        "end": {"date": "2026-11-14"},
                    }
                ]
            },
        ]

        res = self.tools.calendar.list_events(
            start_date="2026-11-12", end_date="2026-11-13"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["count"], 2)

        first = res["data"]["events"][0]
        self.assertEqual(first["id"], "e1")
        self.assertEqual(first["title"], "Morning Coffee")
        self.assertFalse(first["all_day"])
        self.assertEqual(first["attendees"], ["a@example.com"])
        self.assertNotIn("etag", first)

        second = res["data"]["events"][1]
        self.assertTrue(second["all_day"])
        self.assertEqual(second["start"], "2026-11-13")

    def test_check_availability_free_and_conflicts(self) -> None:
        mock_list = self.event_handler.service.events().list
        self.calendar_handler.find_calendar_id_by_name.return_value = (
            "team@group.calendar.google.com"
        )

        # Ignores cancelled & transparent events, flags real conflict
        mock_list.return_value.execute.side_effect = [
            {
                "items": [
                    {
                        "id": "free1",
                        "summary": "Reminder",
                        "start": {"dateTime": "2026-11-12T14:00:00+01:00"},
                        "end": {"dateTime": "2026-11-12T15:00:00+01:00"},
                        "transparency": "transparent",
                    },
                    {
                        "id": "canc1",
                        "summary": "Cancelled Sync",
                        "start": {"dateTime": "2026-11-12T14:00:00+01:00"},
                        "end": {"dateTime": "2026-11-12T15:00:00+01:00"},
                        "status": "cancelled",
                    },
                ]
            },
            {
                "items": [
                    {
                        "id": "busy1",
                        "summary": "Dentist",
                        "start": {"dateTime": "2026-11-12T13:30:00+01:00"},
                        "end": {"dateTime": "2026-11-12T14:30:00+01:00"},
                    }
                ]
            },
        ]

        res = self.tools.calendar.check_availability(
            start="2026-11-12T14:00",
            end="2026-11-12T15:00",
            calendar_names=["primary", "Team"],
        )
        self.assertTrue(res["success"])
        self.assertFalse(res["data"]["available"])
        self.assertEqual(len(res["data"]["conflicts"]), 1)
        conflict = res["data"]["conflicts"][0]
        self.assertEqual(conflict["title"], "Dentist")
        self.assertEqual(conflict["calendar_id"], "team@group.calendar.google.com")

        # Free slot case
        mock_list.return_value.execute.side_effect = [{"items": []}]
        free_res = self.tools.calendar.check_availability(
            start="2026-11-12T16:00Z",
            end="2026-11-12T17:00Z",
        )
        self.assertTrue(free_res["success"])
        self.assertTrue(free_res["data"]["available"])
        self.assertEqual(free_res["data"]["conflicts"], [])

    def test_delete_event_success_and_not_found(self) -> None:
        self.calendar_handler.find_calendar_id_by_name.return_value = (
            "work@group.calendar.google.com"
        )
        ok_res = self.tools.calendar.delete_event(
            event_id="evt_5", calendar_name="Work"
        )
        self.assertTrue(ok_res["success"])
        self.event_handler.delete_event.assert_called_once_with(
            "work@group.calendar.google.com", "evt_5"
        )

        self.event_handler.delete_event.side_effect = _http_error(404, "Not Found")
        missing_res = self.tools.calendar.delete_event(event_id="evt_missing")
        self.assertFalse(missing_res["success"])
        self.assertEqual(missing_res["error_code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
