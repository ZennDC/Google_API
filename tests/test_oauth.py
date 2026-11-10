import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from google.auth.exceptions import GoogleAuthError

from google_api.oauth.auth import (
    _resolve_file_path,
    get_credentials,
    get_credentials_notoken,
)


class TestOAuth(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resolve_file_path_explicit_existing_file(self):
        dummy_file = os.path.join(self.temp_dir.name, "custom_secret.json")
        with open(dummy_file, "w") as f:
            f.write("{}")

        resolved = _resolve_file_path(dummy_file, ["client_secret.json"])
        self.assertEqual(resolved, str(os.path.abspath(dummy_file)))

    def test_resolve_file_path_explicit_nonexistent_returns_path(self):
        dummy_file = os.path.join(self.temp_dir.name, "nonexistent.json")
        resolved = _resolve_file_path(dummy_file, ["client_secret.json"])
        self.assertEqual(resolved, str(os.path.abspath(dummy_file)))

    def test_resolve_file_path_search_dirs_discovery(self):
        # Test default_names resolution when no filename is given
        resolved = _resolve_file_path(None, ["token.json"])
        self.assertTrue(resolved.endswith("token.json"))

        # Test single filename without path searching dirs
        resolved_name = _resolve_file_path("token.json", ["token.json"])
        self.assertTrue(resolved_name.endswith("token.json"))

    @patch("google_api.oauth.auth.Credentials.from_authorized_user_file")
    def test_get_credentials_valid_cached_token(self, mock_from_file):
        token_path = os.path.join(self.temp_dir.name, "token.json")
        with open(token_path, "w") as f:
            f.write('{"token": "fake"}')

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds.valid = True
        mock_creds.has_scopes.return_value = True
        mock_from_file.return_value = mock_creds

        creds = get_credentials(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            token_file=token_path,
        )
        self.assertEqual(creds, mock_creds)
        mock_from_file.assert_called_once_with(
            token_path, ["https://www.googleapis.com/auth/gmail.readonly"]
        )

    @patch("google_api.oauth.auth.Credentials.from_authorized_user_file")
    def test_get_credentials_invalid_user_file_fallback(self, mock_from_file):
        token_path = os.path.join(self.temp_dir.name, "token.json")
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(token_path, "w") as f:
            f.write('{"invalid": "json')
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_from_file.side_effect = ValueError("Corrupt file")

        with patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
            mock_flow = MagicMock()
            mock_creds = MagicMock()
            mock_creds.to_json.return_value = '{"token": "new"}'
            mock_flow.run_local_server.return_value = mock_creds
            mock_flow_cls.return_value = mock_flow

            creds = get_credentials(
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                token_file=token_path,
                client_secret_file=secret_path,
            )
            self.assertEqual(creds, mock_creds)

    @patch("google_api.oauth.auth.Credentials.from_authorized_user_file")
    def test_get_credentials_expired_token_refreshed(self, mock_from_file):
        token_path = os.path.join(self.temp_dir.name, "token.json")
        with open(token_path, "w") as f:
            f.write('{"token": "fake"}')

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "fake_refresh_token"
        mock_creds.valid = True
        mock_creds.has_scopes.return_value = True
        mock_creds.to_json.return_value = '{"refreshed": true}'
        mock_from_file.return_value = mock_creds

        creds = get_credentials(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            token_file=token_path,
        )
        self.assertEqual(creds, mock_creds)
        mock_creds.refresh.assert_called_once()
        with open(token_path) as f:
            self.assertIn("refreshed", f.read())

    @patch("google_api.oauth.auth.Credentials.from_authorized_user_file")
    def test_get_credentials_refresh_failure_falls_back_to_flow(self, mock_from_file):
        token_path = os.path.join(self.temp_dir.name, "token.json")
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(token_path, "w") as f:
            f.write('{"token": "fake"}')
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "fake_refresh_token"
        mock_creds.refresh.side_effect = GoogleAuthError("Token revoked")
        mock_from_file.return_value = mock_creds

        with patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
            mock_flow = MagicMock()
            fresh_creds = MagicMock()
            fresh_creds.to_json.return_value = '{"token": "fresh"}'
            mock_flow.run_local_server.return_value = fresh_creds
            mock_flow_cls.return_value = mock_flow

            creds = get_credentials(
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                token_file=token_path,
                client_secret_file=secret_path,
            )
            self.assertEqual(creds, fresh_creds)

    @patch("google_api.oauth.auth.Credentials.from_authorized_user_file")
    def test_get_credentials_scope_mismatch_triggers_flow(self, mock_from_file):
        token_path = os.path.join(self.temp_dir.name, "token.json")
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(token_path, "w") as f:
            f.write('{"token": "fake"}')
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds.valid = True
        mock_creds.has_scopes.return_value = False
        mock_from_file.return_value = mock_creds

        with patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
            mock_flow = MagicMock()
            new_creds = MagicMock()
            new_creds.to_json.return_value = '{"new": true}'
            mock_flow.run_local_server.return_value = new_creds
            mock_flow_cls.return_value = mock_flow

            creds = get_credentials(
                scopes=["scope1", "scope2"],
                token_file=token_path,
                client_secret_file=secret_path,
            )
            self.assertEqual(creds, new_creds)

    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_launches_flow_when_no_token(self, mock_flow_from_file):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        token_path = os.path.join(self.temp_dir.name, "new_token.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"new_token": true}'
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_from_file.return_value = mock_flow

        creds = get_credentials(
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            token_file=token_path,
            client_secret_file=secret_path,
            save_token=True,
        )

        self.assertEqual(creds, mock_creds)
        mock_flow.run_local_server.assert_called_once_with(port=0)
        self.assertTrue(os.path.exists(token_path))

    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_flow_failure_raises(self, mock_flow_from_file):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = OSError("Port bind error")
        mock_flow_from_file.return_value = mock_flow

        with self.assertRaises(OSError):
            get_credentials(
                scopes=["scope"],
                token_file=os.path.join(self.temp_dir.name, "token.json"),
                client_secret_file=secret_path,
            )

    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_notoken(self, mock_flow_from_file):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_from_file.return_value = mock_flow

        creds = get_credentials_notoken(
            scopes=["https://www.googleapis.com/auth/calendar"],
            client_secret_file=secret_path,
        )
        self.assertEqual(creds, mock_creds)

    def test_get_credentials_missing_secret_raises_error(self):
        missing_secret = os.path.join(self.temp_dir.name, "missing.json")
        with self.assertRaises(FileNotFoundError):
            get_credentials(
                scopes=["scope"],
                token_file=os.path.join(self.temp_dir.name, "token.json"),
                client_secret_file=missing_secret,
            )

    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_custom_port_and_host(self, mock_flow_from_file):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_from_file.return_value = mock_flow

        creds = get_credentials(
            scopes=["scope"],
            client_secret_file=secret_path,
            save_token=False,
            port=8085,
            host="0.0.0.0",
            bind_addr="0.0.0.0",
            open_browser=False,
        )
        self.assertEqual(creds, mock_creds)
        mock_flow.run_local_server.assert_called_once_with(
            port=8085,
            host="0.0.0.0",
            bind_addr="0.0.0.0",
            open_browser=False,
        )

    @patch("builtins.print")
    @patch("builtins.input", return_value="fake_auth_code_123")
    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_headless_console_flow(
        self, mock_flow_from_file, mock_input, mock_print
    ):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_flow.credentials = mock_creds
        mock_flow.authorization_url.return_value = ("https://auth.url", "state123")
        mock_flow_from_file.return_value = mock_flow

        creds = get_credentials(
            scopes=["scope"],
            client_secret_file=secret_path,
            save_token=False,
            headless=True,
        )

        self.assertEqual(creds, mock_creds)
        self.assertEqual(mock_flow.redirect_uri, "urn:ietf:wg:oauth:2.0:oob")
        mock_flow.authorization_url.assert_called_once_with(prompt="consent")
        mock_flow.fetch_token.assert_called_once_with(code="fake_auth_code_123")
        mock_flow.run_local_server.assert_not_called()

    @patch("builtins.print")
    @patch("builtins.input", return_value="http://localhost:8080/?code=extracted_code_456&state=xyz")
    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_headless_full_url_paste(
        self, mock_flow_from_file, mock_input, mock_print
    ):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_flow.credentials = mock_creds
        mock_flow.authorization_url.return_value = ("https://auth.url", "state123")
        mock_flow_from_file.return_value = mock_flow

        creds = get_credentials(
            scopes=["scope"],
            client_secret_file=secret_path,
            save_token=False,
            headless=True,
        )

        self.assertEqual(creds, mock_creds)
        mock_flow.fetch_token.assert_called_once_with(code="extracted_code_456")

    @patch.dict(os.environ, {"GOOGLE_API_HEADLESS": "1"})
    @patch("builtins.print")
    @patch("builtins.input", return_value="env_auth_code")
    @patch("google_api.oauth.auth.InstalledAppFlow.from_client_secrets_file")
    def test_get_credentials_headless_via_env_var(
        self, mock_flow_from_file, mock_input, mock_print
    ):
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_flow.credentials = mock_creds
        mock_flow.authorization_url.return_value = ("https://auth.url", "state123")
        mock_flow_from_file.return_value = mock_flow

        creds = get_credentials(
            scopes=["scope"],
            client_secret_file=secret_path,
            save_token=False,
        )

        self.assertEqual(creds, mock_creds)
        mock_flow.fetch_token.assert_called_once_with(code="env_auth_code")


class TestFactory(unittest.TestCase):
    @patch("google_api.oauth.factory.build")
    @patch("google_api.oauth.factory.get_credentials")
    def test_build_service_with_defaults(self, mock_get_creds, mock_build):
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        from google_api.oauth.factory import GMAIL_SCOPES, build_service

        service = build_service("gmail", "v1")
        self.assertEqual(service, mock_service)
        mock_get_creds.assert_called_once()
        self.assertEqual(mock_get_creds.call_args.kwargs["scopes"], GMAIL_SCOPES)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

    @patch("google_api.oauth.factory.build")
    def test_build_service_explicit_credentials(self, mock_build):
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        from google_api.oauth.factory import build_service

        service = build_service("calendar", "v3", credentials=mock_creds)
        self.assertEqual(service, mock_service)
        mock_build.assert_called_once_with("calendar", "v3", credentials=mock_creds)

    def test_build_service_unknown_service_without_scopes_raises(self):
        from google_api.oauth.factory import build_service

        with self.assertRaises(ValueError):
            build_service("unknown_service", "v1")

    @patch("google_api.oauth.factory.build_service")
    def test_get_gmail_handler_message(self, mock_build_service):
        mock_service = MagicMock()
        mock_build_service.return_value = mock_service

        from google_api.gmail_api.handlers import MessageHandler
        from google_api.oauth.factory import get_gmail_handler

        handler = get_gmail_handler(handler_type="message", include_spam_trash=True)
        self.assertIsInstance(handler, MessageHandler)
        self.assertEqual(handler.service, mock_service)
        self.assertTrue(handler.include_spam_trash)

    @patch("google_api.oauth.factory.build_service")
    def test_get_gmail_handler_label(self, mock_build_service):
        mock_service = MagicMock()
        mock_build_service.return_value = mock_service

        from google_api.gmail_api.handlers import LabelHandler
        from google_api.oauth.factory import get_gmail_handler

        handler = get_gmail_handler(handler_type="label")
        self.assertIsInstance(handler, LabelHandler)
        self.assertEqual(handler.service, mock_service)

    def test_get_gmail_handler_invalid_type_raises(self):
        from google_api.oauth.factory import get_gmail_handler

        with self.assertRaises(ValueError):
            get_gmail_handler(handler_type="invalid")

    @patch("google_api.oauth.factory.build_service")
    def test_get_calendar_handler_event(self, mock_build_service):
        mock_service = MagicMock()
        mock_build_service.return_value = mock_service

        from google_api.google_calendar_api.handlers import EventHandler
        from google_api.oauth.factory import get_calendar_handler

        handler = get_calendar_handler(handler_type="event")
        self.assertIsInstance(handler, EventHandler)
        self.assertEqual(handler.service, mock_service)

    @patch("google_api.oauth.factory.build_service")
    def test_get_calendar_handler_calendar(self, mock_build_service):
        mock_service = MagicMock()
        mock_build_service.return_value = mock_service

        from google_api.google_calendar_api.handlers import CalendarHandler
        from google_api.oauth.factory import get_calendar_handler

        handler = get_calendar_handler(handler_type="calendar")
        self.assertIsInstance(handler, CalendarHandler)
        self.assertEqual(handler.service, mock_service)

    def test_get_calendar_handler_invalid_type_raises(self):
        from google_api.oauth.factory import get_calendar_handler

        with self.assertRaises(ValueError):
            get_calendar_handler(handler_type="invalid")

    @patch("google_api.oauth.factory.build_service")
    def test_convenience_helpers(self, mock_build_service):
        mock_service = MagicMock()
        mock_build_service.return_value = mock_service

        from google_api.gmail_api.handlers import LabelHandler, MessageHandler
        from google_api.google_calendar_api.handlers import EventHandler
        from google_api.oauth.factory import (
            get_calendar_service,
            get_event_handler,
            get_gmail_service,
            get_label_handler,
            get_message_handler,
        )

        svc_gmail = get_gmail_service()
        self.assertEqual(svc_gmail, mock_service)

        svc_cal = get_calendar_service()
        self.assertEqual(svc_cal, mock_service)

        msg_h = get_message_handler()
        self.assertIsInstance(msg_h, MessageHandler)

        lbl_h = get_label_handler()
        self.assertIsInstance(lbl_h, LabelHandler)

        evt_h = get_event_handler()
        self.assertIsInstance(evt_h, EventHandler)


if __name__ == "__main__":
    unittest.main()
