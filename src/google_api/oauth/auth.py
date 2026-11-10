import logging
import os
from pathlib import Path

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger("google_api")


def _get_project_root() -> Path:
    """Returns the root directory of the google_api project."""
    return Path(__file__).resolve().parent.parent


def _resolve_file_path(filename: str | None, default_names: list[str]) -> str:
    """Finds a file path by checking explicit path, secrets/ directory, project root, or current directory."""
    if filename:
        p = Path(filename)
        # If an absolute path or path with parent directories is given, resolve directly
        if p.is_absolute() or len(p.parts) > 1:
            return str(p.resolve())

        # If it's a simple filename, check current directory or search directories
        if p.is_file():
            return str(p.resolve())

        root = _get_project_root()
        search_dirs = [
            root / "secrets",
            root,
            Path.cwd() / "secrets",
            Path.cwd(),
        ]
        for d in search_dirs:
            candidate = d / filename
            if candidate.is_file():
                return str(candidate.resolve())

        return str(p.resolve())

    root = _get_project_root()
    search_dirs = [
        root / "secrets",
        root,
        Path.cwd() / "secrets",
        Path.cwd(),
    ]
    for d in search_dirs:
        for name in default_names:
            candidate = d / name
            if candidate.is_file():
                return str(candidate.resolve())

    return str((root / "secrets" / default_names[0]).resolve())


def get_credentials(
    scopes: list[str],
    token_file: str | None = None,
    client_secret_file: str | None = None,
    save_token: bool = True,
    headless: bool = False,
    port: int = 0,
    host: str = "localhost",
    bind_addr: str | None = None,
    open_browser: bool | None = None,
) -> Credentials:
    """Returns authorized credentials, automatically refreshing or launching OAuth flow if needed.

    Args:
        scopes: OAuth scopes required.
        token_file: Path to the cached token JSON file.
        client_secret_file: Path to client_secret.json.
        save_token: Whether to save/load credentials from token_file.
        headless: If True, uses console copy-paste flow suitable for headless servers/Docker.
            Can also be enabled via the GOOGLE_API_HEADLESS=1 environment variable.
        port: Port for local redirect server (default: 0 for an arbitrary open port).
        host: Hostname for local redirect server (default: 'localhost').
        bind_addr: Optional bind address for local redirect server (e.g., '0.0.0.0' in Docker).
        open_browser: Whether to automatically open the browser during local server flow.
            Defaults to True unless headless is True.
    """
    resolved_secret = _resolve_file_path(
        client_secret_file, ["client_secret.json", "credentials.json"]
    )
    resolved_token = (
        _resolve_file_path(token_file, ["token.json"]) if save_token else None
    )

    creds = None
    if save_token and resolved_token and os.path.exists(resolved_token):
        try:
            creds = Credentials.from_authorized_user_file(resolved_token, scopes)
        except (ValueError, GoogleAuthError):
            creds = None

    if creds:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if save_token and resolved_token:
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

            # Check headless flag or environment variable
            is_headless = headless or os.environ.get(
                "GOOGLE_API_HEADLESS", ""
            ).lower() in ("1", "true", "yes")

            if is_headless:
                flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
                auth_url, _ = flow.authorization_url(prompt="consent")
                print("\n" + "=" * 60)
                print("Headless Authentication Required:")
                print(f"Please visit this URL in any browser:\n{auth_url}")
                print("=" * 60 + "\n")
                code = input(
                    "Enter the authorization code (or full redirect URL): "
                ).strip()
                if "code=" in code:
                    # User pasted the whole redirect URL (e.g. from localhost redirect)
                    from urllib.parse import parse_qs, urlparse

                    parsed = urlparse(code)
                    qs = parse_qs(parsed.query)
                    code = qs.get("code", [code])[0]
                flow.fetch_token(code=code)
                creds = flow.credentials
            else:
                server_kwargs = {"port": port}
                if host != "localhost":
                    server_kwargs["host"] = host
                if bind_addr is not None:
                    server_kwargs["bind_addr"] = bind_addr
                if open_browser is not None:
                    server_kwargs["open_browser"] = open_browser
                creds = flow.run_local_server(**server_kwargs)

            if save_token and resolved_token:
                os.makedirs(os.path.dirname(resolved_token), exist_ok=True)
                with open(resolved_token, "w") as token:
                    token.write(creds.to_json())
        except (GoogleAuthError, OSError) as e:
            logger.error(f"An error occurred during authentication flow: {e}")
            raise

    return creds


def get_credentials_notoken(
    scopes: list[str],
    client_secret_file: str | None = None,
    headless: bool = False,
    port: int = 0,
    host: str = "localhost",
    bind_addr: str | None = None,
    open_browser: bool | None = None,
) -> Credentials:
    """Returns authorized credentials without writing or reading a token file."""
    return get_credentials(
        scopes=scopes,
        client_secret_file=client_secret_file,
        save_token=False,
        headless=headless,
        port=port,
        host=host,
        bind_addr=bind_addr,
        open_browser=open_browser,
    )
