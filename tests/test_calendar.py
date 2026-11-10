import unittest
from unittest.mock import MagicMock

import httplib2
from googleapiclient.errors import HttpError

from google_api.calendar.handlers import CalendarHandler, EventHandler
from google_api.calendar.objects import (
    Calendar,
    CalendarList,
    Event,
    TimedEvent,
    convert_date,
    convert_time,
    validate_time_zone,
)


class TestCalendarDateAndTime(unittest.TestCase):
    def test_convert_date(self):
        result = convert_date(
            "25/12/2026", input_format="%d/%m/%Y", output_format="%Y-%m-%d"
        )
        self.assertEqual(result, "2026-12-25")

        reversed_date = convert_date(
            "2026-12-25",
            reverse=True,
            input_format="%d/%m/%Y",
            output_format="%Y-%m-%d",
        )
        self.assertEqual(reversed_date, "25/12/2026")

        added_day = convert_date("25/12/2026", add_day=True)
        self.assertEqual(added_day, "2026-12-26")

        added_day_reversed = convert_date("2026-12-25", reverse=True, add_day=True)
        self.assertEqual(added_day_reversed, "26/12/2026")

        with self.assertRaises(ValueError):
            convert_date("invalid-date-format")

    def test_convert_time_formats(self):
        self.assertEqual(convert_time("14:30"), "14:30:00")
        self.assertEqual(convert_time("14:30:45"), "14:30:45")
        self.assertEqual(convert_time("14u30"), "14:30:00")

        # Reversed convert_time
        reversed_time = convert_time(
            "14:30:00", reverse=True, input_format="%Hu%M", output_format="%H:%M:00"
        )
        self.assertEqual(reversed_time, "14u30")

        with self.assertRaises(ValueError):
            convert_time("invalid-time-format")

    def test_time_comparison(self):
        self.assertTrue(EventHandler.is_greater("15:00", "14:30"))
        self.assertTrue(EventHandler.is_greater("14:30", "14:30"))
        self.assertFalse(EventHandler.is_greater("12:00", "14:30"))
        self.assertTrue(EventHandler.is_greater("14:30:05", "14:30:00"))
        self.assertFalse(EventHandler.is_greater("14:30:00", "14:30:05"))

    def test_event_handler_date_conversion(self):
        handler = EventHandler(service=None)
        self.assertEqual(handler.convert_date("10 januari 2026"), "10/1/2026")
        self.assertEqual(handler.convert_date("25/12/2026"), "25/12/2026")
        self.assertEqual(handler.convert_date("2026-05-18"), "18/5/2026")
        with self.assertRaises(ValueError):
            handler.convert_date("not a date at all")
        with self.assertRaises(KeyError):
            handler.convert_date("10 notamonth 2026")

    def test_event_handler_time_conversion(self):
        handler = EventHandler(service=None)
        start, end = handler.convert_time("From 10:00 to 11:30")
        self.assertEqual(start, "10:00")
        self.assertEqual(end, "11:30")

        with self.assertRaises(ValueError):
            handler.convert_time("No times here")

    def test_validators(self):
        self.assertTrue(validate_time_zone("Europe/Brussels"))
        self.assertTrue(validate_time_zone("UTC"))
        self.assertFalse(validate_time_zone("Invalid/Zone"))


class TestCalendarDataclasses(unittest.TestCase):
    def test_calendar_build(self):
        cal = Calendar(
            title="Team Calendar", description="Work projects", location="Office"
        )
        built = cal.build()
        self.assertEqual(built["summary"], "Team Calendar")
        self.assertEqual(built["description"], "Work projects")
        self.assertEqual(built["location"], "Office")
        self.assertEqual(built["timeZone"], "Europe/Brussels")

    def test_calendar_from_json(self):
        sample = {
            "summary": "Imported Cal",
            "timeZone": "UTC",
            "description": "Desc",
            "location": "Loc",
            "id": "cal_id",
            "kind": "calendar#calendar",
            "etag": '"etag"',
        }
        cal = Calendar.from_json(sample)
        self.assertEqual(cal.title, "Imported Cal")
        self.assertEqual(cal.time_zone, "UTC")

        with self.assertRaises(ValueError):
            Calendar.from_json({"invalid": "no summary"})

    def test_calendar_list_build(self):
        cal_list = CalendarList(
            id="primary",
            color_id="1",
            background_color="#123456",
            foreground_color="#ffffff",
            hidden=True,
            selected=True,
            summary_override="My Override",
            default_reminders=[{"method": "popup", "minutes": 10}],
            notification_settings={"notifications": []},
        )
        built = cal_list.build()
        self.assertEqual(built["id"], "primary")
        self.assertEqual(built["colorId"], "1")
        self.assertEqual(built["backgroundColor"], "#123456")
        self.assertEqual(built["foregroundColor"], "#ffffff")
        self.assertTrue(built["hidden"])
        self.assertTrue(built["selected"])
        self.assertEqual(built["summaryOverride"], "My Override")
        self.assertEqual(len(built["defaultReminders"]), 1)
        self.assertIn("notifications", built["notificationSettings"])

    def test_calendar_list_from_json(self):
        sample = {
            "id": "list_id",
            "backgroundColor": "#000",
            "summaryOverride": "Overridden",
        }
        entry = CalendarList.from_json(sample)
        self.assertEqual(entry.id, "list_id")
        self.assertEqual(entry.background_color, "#000")
        self.assertEqual(entry.summary_override, "Overridden")

    def test_event_build(self):
        event = Event(
            title="Conference",
            start_date="01/06/2026",
            end_date="03/06/2026",
            location="Brussels Expo",
            description="Tech convention",
        )
        built = event.build()
        self.assertEqual(built["summary"], "Conference")
        self.assertEqual(built["start"]["date"], "2026-06-01")
        self.assertEqual(built["end"]["date"], "2026-06-03")
        self.assertEqual(built["location"], "Brussels Expo")
        self.assertEqual(built["description"], "Tech convention")
        self.assertNotIn("dateTime", built["start"])

    def test_event_build_with_recurrence_attendees_reminders(self):
        event = Event(
            title="Weekly Team Sync",
            start_date="01/06/2026",
            end_date="01/06/2026",
            recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
            attendees=[
                "alice@example.com",
                {"email": "bob@example.com", "displayName": "Bob"},
            ],
            reminders={
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 15}],
            },
        )
        built = event.build()
        self.assertEqual(built["summary"], "Weekly Team Sync")
        self.assertEqual(built["recurrence"], ["RRULE:FREQ=WEEKLY;BYDAY=MO"])
        self.assertEqual(
            built["attendees"],
            [
                {"email": "alice@example.com"},
                {"email": "bob@example.com", "displayName": "Bob"},
            ],
        )
        self.assertEqual(
            built["reminders"],
            {"useDefault": False, "overrides": [{"method": "popup", "minutes": 15}]},
        )

        # Single string recurrence normalization
        event_str_rec = Event(
            title="Single string recurrence",
            start_date="01/06/2026",
            end_date="01/06/2026",
            recurrence="RRULE:FREQ=DAILY",
        )
        self.assertEqual(event_str_rec.build()["recurrence"], ["RRULE:FREQ=DAILY"])

    def test_timed_event_build(self):
        timed = TimedEvent(
            title="Meeting",
            start_date="01/06/2026",
            end_date="01/06/2026",
            start_time="10:00",
            end_time="11:00",
            time_format="%H:%M",
        )
        built = timed.build()
        self.assertEqual(built["summary"], "Meeting")
        self.assertEqual(built["start"]["dateTime"], "2026-06-01T10:00:00")
        self.assertEqual(built["end"]["dateTime"], "2026-06-01T11:00:00")
        self.assertNotIn("date", built["start"])
        self.assertNotIn("date", built["end"])


class TestCalendarHandlers(unittest.TestCase):
    def test_find_calendar_id_by_name_pagination(self):
        mock_service = MagicMock()
        mock_list = mock_service.calendarList().list

        mock_list.side_effect = [
            MagicMock(
                execute=lambda: {
                    "items": [{"id": "cal1", "summary": "Other"}],
                    "nextPageToken": "token2",
                }
            ),
            MagicMock(
                execute=lambda: {
                    "items": [{"id": "target_id", "summary": "My Work"}],
                    "nextPageToken": None,
                }
            ),
        ]

        handler = CalendarHandler(mock_service)
        cal_id = handler.find_calendar_id_by_name("My Work")
        self.assertEqual(cal_id, "target_id")

        # Test primary shortcut and convenience alias
        self.assertEqual(handler.get_calendar_id("primary"), "primary")

    def test_calendar_crud_operations(self):
        mock_service = MagicMock()
        handler = CalendarHandler(mock_service)

        # Create with Calendar object
        mock_service.calendars().insert().execute.return_value = {"id": "new_cal_id"}
        cal = Calendar(title="New Calendar")
        created_id = handler.create_calendar(cal)
        self.assertEqual(created_id, "new_cal_id")

        # Create with raw dict
        handler.create_calendar({"summary": "Dict Calendar"})

        # Get
        mock_service.calendars().get().execute.return_value = {
            "id": "cal_123@group.calendar.google.com",
            "summary": "Existing",
        }
        res = handler.get_calendar("cal_123@group.calendar.google.com")
        self.assertEqual(res["summary"], "Existing")

        # Update
        handler.update_calendar(
            "cal_123@group.calendar.google.com", {"summary": "Updated"}
        )
        mock_service.calendars().update.assert_called_with(
            calendarId="cal_123@group.calendar.google.com", body={"summary": "Updated"}
        )

        # Delete
        handler.delete_calendar("cal_123@group.calendar.google.com")
        mock_service.calendars().delete.assert_called_with(
            calendarId="cal_123@group.calendar.google.com"
        )

        # Clear
        handler.clear_calendar("cal_123@group.calendar.google.com")
        mock_service.calendars().clear.assert_called_with(
            calendarId="cal_123@group.calendar.google.com"
        )

    def test_calendar_list_operations(self):
        mock_service = MagicMock()
        handler = CalendarHandler(mock_service)

        # Get list entry
        mock_service.calendarList().get().execute.return_value = {
            "id": "cal_123@group.calendar.google.com"
        }
        entry = handler.get_calendar_list_entry("cal_123@group.calendar.google.com")
        self.assertEqual(entry["id"], "cal_123@group.calendar.google.com")

        # Update list entry
        handler.update_calendar_list_entry(
            "cal_123@group.calendar.google.com", {"colorId": "2"}
        )
        mock_service.calendarList().update.assert_called_with(
            calendarId="cal_123@group.calendar.google.com", body={"colorId": "2"}
        )

        # Delete from list
        handler.delete_calendar_from_list("cal_123@group.calendar.google.com")
        mock_service.calendarList().delete.assert_called_with(
            calendarId="cal_123@group.calendar.google.com"
        )

        # Add existing calendar
        mock_service.calendarList().insert().execute.return_value = {"id": "added_id"}
        added = handler.add_existing_calendar({"id": "added_id"})
        self.assertEqual(added["id"], "added_id")

        # List all calendars with pagination
        mock_service.calendarList().list().execute.side_effect = [
            {"items": [{"id": "c1"}], "nextPageToken": "p2"},
            {"items": [{"id": "c2"}], "nextPageToken": None},
        ]
        all_cals = handler.list_all_calendars()
        self.assertEqual(len(all_cals), 2)

    def test_calendar_error_handling(self):
        mock_service = MagicMock()
        resp = httplib2.Response({"status": 500, "reason": "Server Error"})
        mock_service.calendars().get().execute.side_effect = HttpError(
            resp, b"Server Error"
        )

        handler = CalendarHandler(mock_service)
        with self.assertRaises(HttpError):
            handler.get_calendar("bad_id@group.calendar.google.com")

        # When calendar cannot be resolved and is None
        with unittest.mock.patch.object(
            handler, "_resolve_calendar_id", return_value=None
        ):
            self.assertIsNone(handler.get_calendar("missing"))
            handler.clear_calendar("missing")
            handler.delete_calendar("missing")
            handler.update_calendar("missing", {})
            handler.delete_calendar_from_list("missing")
            self.assertIsNone(handler.get_calendar_list_entry("missing"))
            handler.update_calendar_list_entry("missing", {})

    def test_plan_event_and_remove_duplicates(self):
        mock_service = MagicMock()
        event_handler = EventHandler(mock_service)

        # Plan event with Event object
        mock_service.events().insert().execute.return_value = {"id": "ev_1"}
        ev = Event(title="Test", start_date="01/01/2026", end_date="01/01/2026")
        res = event_handler.plan_event("primary", ev)
        self.assertEqual(res["id"], "ev_1")

        # Plan event with dict
        res_dict = event_handler.plan_event("primary", {"summary": "Raw Dict"})
        self.assertEqual(res_dict["id"], "ev_1")

        # Remove duplicates
        mock_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "ev_1",
                    "summary": "Duplicate",
                    "start": {"dateTime": "2026-01-01T10:00:00Z"},
                },
                {
                    "id": "ev_2",
                    "summary": "Duplicate",
                    "start": {"dateTime": "2026-01-01T10:00:00Z"},
                },
                {
                    "id": "ev_3",
                    "summary": "Unique",
                    "start": {"dateTime": "2026-01-01T11:00:00Z"},
                },
            ]
        }
        event_handler.remove_duplicates("primary", "2026-01-01")
        mock_service.events().delete.assert_called_once_with(
            calendarId="primary", eventId="ev_2"
        )

    def test_get_event(self):
        mock_service = MagicMock()
        event_handler = EventHandler(mock_service)
        mock_service.events().get().execute.return_value = {
            "id": "ev_123",
            "summary": "Sample Event",
        }

        result = event_handler.get_event("primary", "ev_123")
        self.assertEqual(result["id"], "ev_123")
        mock_service.events().get.assert_called_with(
            calendarId="primary", eventId="ev_123"
        )

        resp = httplib2.Response({"status": 404, "reason": "Not Found"})
        mock_service.events().get().execute.side_effect = HttpError(resp, b"Not Found")
        with self.assertRaises(HttpError):
            event_handler.get_event("primary", "missing_id")

    def test_update_event(self):
        mock_service = MagicMock()
        event_handler = EventHandler(mock_service)

        # Full update (PUT) with TimedEvent
        mock_service.events().update().execute.return_value = {
            "id": "ev_123",
            "summary": "Updated Title",
        }
        ev = TimedEvent(
            title="Updated Title",
            start_date="01/01/2026",
            end_date="01/01/2026",
            start_time="09:00",
            end_time="10:00",
        )
        updated = event_handler.update_event("primary", "ev_123", ev, patch=False)
        self.assertEqual(updated["summary"], "Updated Title")
        mock_service.events().update.assert_called_with(
            calendarId="primary",
            eventId="ev_123",
            body=ev.build(),
        )

        # Patch (PATCH) with dict (default patch=True)
        mock_service.events().patch().execute.return_value = {
            "id": "ev_123",
            "summary": "Patched Title",
        }
        patched = event_handler.update_event(
            "primary", "ev_123", {"summary": "Patched Title"}
        )
        self.assertEqual(patched["summary"], "Patched Title")
        mock_service.events().patch.assert_called_with(
            calendarId="primary",
            eventId="ev_123",
            body={"summary": "Patched Title"},
        )

        # Error handling
        resp = httplib2.Response({"status": 500, "reason": "Server Error"})
        mock_service.events().patch().execute.side_effect = HttpError(
            resp, b"Server Error"
        )
        with self.assertRaises(HttpError):
            event_handler.update_event("primary", "ev_123", ev)

    def test_get_events_pagination(self):
        mock_service = MagicMock()
        event_handler = EventHandler(mock_service)

        mock_service.events().list().execute.side_effect = [
            {
                "items": [{"id": "ev_p1_1"}, {"id": "ev_p1_2"}],
                "nextPageToken": "token_page_2",
            },
            {
                "items": [{"id": "ev_p2_1"}],
                "nextPageToken": None,
            },
        ]

        events = event_handler.get_events("primary", "2026-06-01")
        self.assertEqual(len(events), 3)
        self.assertEqual([e["id"] for e in events], ["ev_p1_1", "ev_p1_2", "ev_p2_1"])

        # Error handling
        resp = httplib2.Response({"status": 500, "reason": "Server Error"})
        mock_service.events().list().execute.side_effect = HttpError(
            resp, b"Server Error"
        )
        with self.assertRaises(HttpError):
            event_handler.get_events("primary", "2026-06-01")

    def test_context_managers_and_close(self):
        mock_service = MagicMock()
        mock_service.close = MagicMock()

        # EventHandler context manager
        with EventHandler(mock_service) as handler:
            self.assertIsInstance(handler, EventHandler)
        mock_service.close.assert_called_once()

        mock_service.close.reset_mock()
        # CalendarHandler context manager
        with CalendarHandler(mock_service) as handler:
            self.assertIsInstance(handler, CalendarHandler)
        mock_service.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
