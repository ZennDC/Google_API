import unittest
from unittest.mock import MagicMock

from google_calendar_api.handlers import CalendarHandler, EventHandler
from google_calendar_api.objects import (
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

    def test_convert_time_formats(self):
        # Default handles standard formats
        self.assertEqual(convert_time("14:30"), "14:30:00")
        self.assertEqual(convert_time("14:30:45"), "14:30:45")
        self.assertEqual(convert_time("14u30"), "14:30:00")

    def test_time_comparison(self):
        self.assertTrue(EventHandler.is_greater("15:00", "14:30"))
        self.assertTrue(EventHandler.is_greater("14:30", "14:30"))
        self.assertFalse(EventHandler.is_greater("12:00", "14:30"))
        # With seconds
        self.assertTrue(EventHandler.is_greater("14:30:05", "14:30:00"))
        self.assertFalse(EventHandler.is_greater("14:30:00", "14:30:05"))

    def test_event_handler_date_conversion(self):
        handler = EventHandler(service=None)
        self.assertEqual(handler.convert_date("10 januari 2026"), "10/1/2026")
        self.assertEqual(handler.convert_date("25/12/2026"), "25/12/2026")
        self.assertEqual(handler.convert_date("2026-05-18"), "18/5/2026")
        with self.assertRaises(KeyError):
            handler.convert_date("10 notamonth 2026")

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

    def test_calendar_list_build(self):
        cal_list = CalendarList(
            id="primary", background_color="#123456", hidden=False, selected=True
        )
        built = cal_list.build()
        self.assertEqual(built["id"], "primary")
        self.assertEqual(built["backgroundColor"], "#123456")
        self.assertTrue(built["selected"])

    def test_event_build(self):
        event = Event(
            title="Conference", start_date="01/06/2026", end_date="03/06/2026"
        )
        built = event.build()
        self.assertEqual(built["summary"], "Conference")
        self.assertEqual(built["start"]["date"], "2026-06-01")
        self.assertEqual(built["end"]["date"], "2026-06-03")
        self.assertNotIn("dateTime", built["start"])

    def test_timed_event_build(self):
        timed = TimedEvent(
            title="Meeting",
            start_date="01/06/2026",
            end_date="01/06/2026",
            start_time="10:00",
            end_time="11:00",
        )
        built = timed.build()
        self.assertEqual(built["summary"], "Meeting")
        self.assertEqual(built["start"]["dateTime"], "2026-06-01T10:00:00")
        self.assertEqual(built["end"]["dateTime"], "2026-06-01T11:00:00")
        self.assertNotIn("date", built["start"])
        self.assertNotIn("date", built["end"])


class TestCalendarHandler(unittest.TestCase):
    def test_find_calendar_id_by_name_pagination(self):
        mock_service = MagicMock()
        mock_list = mock_service.calendarList().list

        # First page has other calendar, nextPageToken set
        # Second page has target calendar
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

    def test_get_events_with_timezone(self):
        mock_service = MagicMock()
        mock_events = mock_service.events().list
        mock_events.return_value.execute.return_value = {"items": [{"id": "ev1"}]}

        handler = EventHandler(mock_service)
        events = handler.get_events(
            "primary", "2026-06-01", time_zone="Europe/Brussels"
        )

        self.assertEqual(len(events), 1)
        mock_events.assert_called_once_with(
            calendarId="primary",
            timeMin="2026-06-01T00:00:00Z",
            timeMax="2026-06-01T23:59:59Z",
            singleEvents=True,
            orderBy="startTime",
            timeZone="Europe/Brussels",
        )


if __name__ == "__main__":
    unittest.main()
