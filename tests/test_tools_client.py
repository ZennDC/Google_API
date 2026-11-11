import inspect
import types
import unittest
from typing import Union, get_args, get_origin, get_type_hints
from unittest.mock import MagicMock, patch

from google_api.oauth.factory import CALENDAR_SCOPES, GMAIL_SCOPES
from google_api.tools import (
    DEFAULT_TIME_ZONE,
    CalendarTools,
    GmailTools,
    GoogleAPITools,
)

_ALLOWED_PRIMITIVES = {str, int, float, bool}


def _is_allowed_tool_param_type(annotation: object) -> bool:
    if annotation in _ALLOWED_PRIMITIVES:
        return True
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        return args == (str,)
    if origin in (Union, types.UnionType):
        args = tuple(a for a in get_args(annotation) if a is not type(None))
        return len(args) == 1 and _is_allowed_tool_param_type(args[0])
    return False


class TestGoogleAPIToolsClient(unittest.TestCase):
    def test_defaults_and_timezone_validation(self) -> None:
        tools = GoogleAPITools()
        self.assertEqual(tools.default_time_zone, DEFAULT_TIME_ZONE)
        self.assertFalse(tools.is_authenticated)

        tools.default_time_zone = "America/New_York"
        self.assertEqual(tools.default_time_zone, "America/New_York")
        self.assertEqual(tools.calendar.default_time_zone, "America/New_York")

        with self.assertRaises(ValueError):
            GoogleAPITools(default_time_zone="Invalid/Zone")

        with self.assertRaises(ValueError):
            tools.default_time_zone = "Mars/Olympus"

    @patch("google_api.tools.calendar_tools.get_calendar_service")
    @patch("google_api.tools.gmail_tools.get_gmail_service")
    @patch("google_api.tools.client.get_credentials")
    def test_authenticate_success_unified_scopes(
        self, mock_get_creds, mock_gmail_svc, mock_cal_svc
    ) -> None:
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_gmail_svc.return_value = MagicMock()
        mock_cal_svc.return_value = MagicMock()

        tools = GoogleAPITools(
            token_file="custom_token.json",
            client_secret_file="custom_secret.json",
            headless=True,
        )
        result = tools.authenticate()

        self.assertTrue(result)
        self.assertTrue(tools.is_authenticated)
        self.assertTrue(tools.gmail.is_authenticated)
        self.assertTrue(tools.calendar.is_authenticated)
        self.assertIsNone(tools.last_error)
        mock_get_creds.assert_called_once_with(
            scopes=[*GMAIL_SCOPES, *CALENDAR_SCOPES],
            token_file="custom_token.json",
            client_secret_file="custom_secret.json",
            save_token=True,
            headless=True,
        )
        mock_gmail_svc.assert_called_once_with(credentials=mock_creds)
        mock_cal_svc.assert_called_once_with(credentials=mock_creds)

    @patch("google_api.tools.calendar_tools.get_calendar_service")
    @patch("google_api.tools.gmail_tools.get_gmail_service")
    @patch("google_api.tools.client.get_credentials")
    def test_authenticate_service_filtering(
        self, mock_get_creds, mock_gmail_svc, mock_cal_svc
    ) -> None:
        mock_get_creds.return_value = MagicMock()
        mock_cal_svc.return_value = MagicMock()

        cal_only = GoogleAPITools(include_gmail=False, include_calendar=True)
        self.assertTrue(cal_only.authenticate())
        self.assertEqual(mock_get_creds.call_args.kwargs["scopes"], CALENDAR_SCOPES)
        mock_gmail_svc.assert_not_called()
        self.assertEqual(len(cal_only.get_gmail_tools()), 0)
        self.assertEqual(len(cal_only.get_calendar_tools()), 4)
        self.assertEqual(len(cal_only.get_tools()), 4)

        resp = cal_only.gmail.list_emails()
        self.assertFalse(resp["success"])
        self.assertEqual(resp["error_code"], "INVALID_INPUT")

    @patch("google_api.tools.client.get_credentials")
    def test_authenticate_failure_returns_false_and_sets_error(
        self, mock_get_creds
    ) -> None:
        mock_get_creds.side_effect = FileNotFoundError("client_secret.json missing")
        tools = GoogleAPITools()

        self.assertFalse(tools.authenticate())
        self.assertFalse(tools.is_authenticated)
        self.assertIn("client_secret.json missing", tools.last_error or "")

        # Lazy auth on tool call returns AUTH_ERROR instead of raising
        resp = tools.gmail.list_emails()
        self.assertFalse(resp["success"])
        self.assertEqual(resp["error_code"], "AUTH_ERROR")

    def test_authenticate_fails_when_all_services_disabled(self) -> None:
        tools = GoogleAPITools(include_gmail=False, include_calendar=False)
        self.assertFalse(tools.authenticate())
        self.assertFalse(tools.is_authenticated)
        self.assertIsNotNone(tools.last_error)

    @patch("google_api.tools.gmail_tools.get_gmail_service")
    @patch("google_api.tools._base.get_credentials")
    def test_standalone_gmail_and_calendar_tools_auth(
        self, mock_get_creds, mock_gmail_svc
    ) -> None:
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_gmail_svc.return_value = MagicMock()

        gmail = GmailTools(token_file="g_token.json")
        self.assertTrue(gmail.authenticate())
        self.assertTrue(gmail.is_authenticated)
        self.assertEqual(len(gmail.get_tools()), 5)
        mock_get_creds.assert_called_once_with(
            scopes=GMAIL_SCOPES,
            token_file="g_token.json",
            client_secret_file=None,
            save_token=True,
            headless=False,
        )

        cal = CalendarTools(default_time_zone="UTC")
        self.assertEqual(cal.default_time_zone, "UTC")
        self.assertEqual(len(cal.get_tools()), 4)

    def test_context_manager_closes_unique_services(self) -> None:
        gmail_svc = MagicMock()
        cal_svc = MagicMock()
        msg_h = MagicMock(service=gmail_svc)
        lbl_h = MagicMock(service=gmail_svc)
        evt_h = MagicMock(service=cal_svc)
        cal_h = MagicMock(service=cal_svc)

        with GoogleAPITools(
            message_handler=msg_h,
            label_handler=lbl_h,
            event_handler=evt_h,
            calendar_handler=cal_h,
        ) as tools:
            self.assertTrue(tools.is_authenticated)

        self.assertFalse(tools.is_authenticated)
        self.assertFalse(tools.gmail.is_authenticated)
        self.assertFalse(tools.calendar.is_authenticated)
        msg_h.close.assert_called_once()
        lbl_h.close.assert_not_called()
        evt_h.close.assert_called_once()
        cal_h.close.assert_not_called()

    def test_rule1_all_bound_tools_use_primitives_only(self) -> None:
        tools = GoogleAPITools()
        bound_tools = tools.get_tools()
        self.assertEqual(len(bound_tools), 9)
        self.assertEqual(len(tools.get_gmail_tools()), 5)
        self.assertEqual(len(tools.get_calendar_tools()), 4)

        for fn in bound_tools:
            with self.subTest(tool=fn.__name__):
                self.assertTrue(bool((fn.__doc__ or "").strip()))
                sig = inspect.signature(fn)
                self.assertNotIn("self", sig.parameters)
                hints = get_type_hints(fn)
                for param_name in sig.parameters:
                    self.assertIn(param_name, hints)
                    self.assertTrue(
                        _is_allowed_tool_param_type(hints[param_name]),
                        f"{fn.__name__}.{param_name} has non-primitive hint {hints[param_name]}",
                    )


if __name__ == "__main__":
    unittest.main()
