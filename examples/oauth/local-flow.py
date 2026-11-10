from google.auth.exceptions import GoogleAuthError

from google_api import GMAIL_SCOPES, get_credentials


def main():
    """Demonstrates acquiring OAuth credentials using the local redirect browser flow."""
    try:
        # Requests authorization using the standard default Gmail scopes
        creds = get_credentials(
            scopes=GMAIL_SCOPES,
            token_file="token.json",
            client_secret_file="client_secret.json",
        )
        print("Successfully obtained credentials via local server flow.")
        print(f"Token is valid: {creds.valid}")
        print(f"Token expired: {creds.expired}")

    except GoogleAuthError as error:
        print(f"Authentication error: {error}")


if __name__ == "__main__":
    main()
