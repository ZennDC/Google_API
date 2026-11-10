import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from google.auth.exceptions import GoogleAuthError

from oauth.auth import _resolve_file_path, get_credentials, get_credentials_notoken


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

    @patch("oauth.auth.Credentials.from_authorized_user_file")
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

    @patch("oauth.auth.Credentials.from_authorized_user_file")
    def test_get_credentials_invalid_user_file_fallback(self, mock_from_file):
        token_path = os.path.join(self.temp_dir.name, "token.json")
        secret_path = os.path.join(self.temp_dir.name, "client_secret.json")
        with open(token_path, "w") as f:
            f.write('{"invalid": "json')
        with open(secret_path, "w") as f:
            f.write('{"installed": {}}')

        mock_from_file.side_effect = ValueError("Corrupt file")

        with patch("oauth.auth.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
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

    @patch("oauth.auth.Credentials.from_authorized_user_file")
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

    @patch("oauth.auth.Credentials.from_authorized_user_file")
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

        with patch("oauth.auth.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
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

    @patch("oauth.auth.Credentials.from_authorized_user_file")
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

        with patch("oauth.auth.InstalledAppFlow.from_client_secrets_file") as mock_flow_cls:
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

    @patch("oauth.auth.InstalledAppFlow.from_client_secrets_file")
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

    @patch("oauth.auth.InstalledAppFlow.from_client_secrets_file")
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

    @patch("oauth.auth.InstalledAppFlow.from_client_secrets_file")
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


if __name__ == "__main__":
    unittest.main()
