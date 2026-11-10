from google.auth.exceptions import GoogleAuthError

from google_api import CALENDAR_SCOPES, get_credentials


def main():
    """Demonstrates console/headless authorization without starting a local web server.

    Useful for remote servers, Docker containers, or SSH sessions where a browser
    cannot be automatically launched or redirect to localhost.
    """
    try:
        creds = get_credentials(
            scopes=CALENDAR_SCOPES,
            token_file="token.json",
            client_secret_file="client_secret.json",
            headless=True,
        )
        print("Successfully obtained credentials via headless/console flow.")
        print(f"Token is valid: {creds.valid}")

    except GoogleAuthError as error:
        print(f"Authentication error: {error}")


if __name__ == "__main__":
    main()
