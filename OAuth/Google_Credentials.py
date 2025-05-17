from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def get_credentials(token_file: str, client_secret_file: str, scopes: list[str]):
    """Returns credentials, renews them or creates new ones if necessary"""
    try:
        creds = Credentials.from_authorized_user_file(token_file)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

            with open(token_file, 'w') as token:
                token.write(creds.to_json())

        if not creds.has_scopes(scopes) or not creds.valid:
            creds = None

    except Exception:
        creds = None

    if not creds:
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0)

            with open(token_file, 'w') as token:
                token.write(creds.to_json())

        except Exception as e:
            print(f"An error occured: {e}")

    return creds

def get_credentials_notoken(client_secret_file: str, scopes: list[str]):
    try:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
        creds = flow.run_local_server(port=0)

        return creds

    except Exception as e:
        print(f"An error occured: {e}")
