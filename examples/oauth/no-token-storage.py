from google.auth.exceptions import GoogleAuthError

from google_api import GMAIL_SCOPES, get_credentials_notoken


def main():
    """Demonstrates obtaining in-memory credentials without reading or persisting token.json.

    Useful for ephemeral sessions, automated CI test environments, or restricted filesystems.
    """
    try:
        creds = get_credentials_notoken(
            scopes=GMAIL_SCOPES,
            client_secret_file="client_secret.json",
        )
        print("Successfully obtained in-memory credentials (no token saved to disk).")
        print(f"Token is valid: {creds.valid}")

    except GoogleAuthError as error:
        print(f"Authentication error: {error}")


if __name__ == "__main__":
    main()
