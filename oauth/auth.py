import os
from pathlib import Path

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..logging_config import logger


def _get_project_root() -> Path:
    """Returns the root directory of the google_api project."""
    return Path(__file__).resolve().parent.parent


def _resolve_file_path(filename: str | None, default_names: list[str]) -> str:
    """Finds a file path by checking explicit path, secrets/ directory, project root, or current directory."""
    root = _get_project_root()
    search_dirs = [
        root / "secrets",
        root,
        Path.cwd() / "secrets",
        Path.cwd(),
    ]

    if filename:
        p = Path(filename)
        if p.is_file():
            return str(p.resolve())
        # Try searching in search_dirs
        for d in search_dirs:
            candidate = d / filename
            if candidate.is_file():
                return str(candidate.resolve())
        # If not found yet, default to secrets/ dir under root or relative
        return str((root / "secrets" / filename).resolve())

    # No filename given: search for any default name
    for d in search_dirs:
        for name in default_names:
            candidate = d / name
            if candidate.is_file():
                return str(candidate.resolve())

    # Fallback to the first default name in secrets/
    return str((root / "secrets" / default_names[0]).resolve())


def get_credentials(
    scopes: list[str],
    token_file: str | None = None,
    client_secret_file: str | None = None,
):
    """Returns credentials, renews them or creates new ones if necessary.

    Parameters can be passed as (scopes) or (token_file, client_secret_file, scopes) for backward compatibility.
    """
    # Handle backward-compatible argument order: (token_file, client_secret_file, scopes)
    if (
        isinstance(scopes, str)
        and isinstance(token_file, str)
        and isinstance(client_secret_file, list)
    ):
        token_file, client_secret_file, scopes = scopes, token_file, client_secret_file

    resolved_token = _resolve_file_path(token_file, ["token.json"])
    resolved_secret = _resolve_file_path(
        client_secret_file, ["client_secret.json", "credentials.json"]
    )

    creds = None
    if os.path.exists(resolved_token):
        try:
            creds = Credentials.from_authorized_user_file(resolved_token, scopes)
        except (ValueError, GoogleAuthError):
            creds = None

    if creds:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(resolved_token, "w") as token:
                    token.write(creds.to_json())
            except GoogleAuthError as e:
                logger.warning(f"Failed to refresh token: {e}")
                creds = None

        if creds and (not creds.has_scopes(scopes) or not creds.valid):
            creds = None

    if not creds:
        if not os.path.exists(resolved_secret):
            raise FileNotFoundError(
                f"Client secret file not found. Looked for {resolved_secret}. "
                f"Please place client_secret.json in the 'secrets/' folder."
            )
        try:
            flow = InstalledAppFlow.from_client_secrets_file(resolved_secret, scopes)
            creds = flow.run_local_server(port=0)

            os.makedirs(os.path.dirname(resolved_token), exist_ok=True)
            with open(resolved_token, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            logger.error(f"An error occurred during authentication flow: {e}")
            raise

    return creds


def get_credentials_notoken(
    client_secret_file: str | None = None, scopes: list[str] | None = None
):
    """Returns credentials without using a token file."""
    if isinstance(client_secret_file, list) and scopes is None:
        scopes, client_secret_file = client_secret_file, None

    resolved_secret = _resolve_file_path(
        client_secret_file, ["client_secret.json", "credentials.json"]
    )

    if not os.path.exists(resolved_secret):
        raise FileNotFoundError(
            f"Client secret file not found: {resolved_secret}. "
            f"Please place client_secret.json in the 'secrets/' folder."
        )

    flow = InstalledAppFlow.from_client_secrets_file(resolved_secret, scopes)
    creds = flow.run_local_server(port=0)
    return creds
