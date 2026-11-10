import os
import sys
from os.path import dirname
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def _get_path():
    """Returns the path of the main executing script directory, falling back to this module's directory"""
    main_mod = sys.modules.get("__main__")
    if main_mod and hasattr(main_mod, "__file__") and main_mod.__file__:
        return dirname(os.path.abspath(main_mod.__file__))
    return dirname(os.path.abspath(__file__))

def get_credentials(token_file: str, client_secret_file: str, scopes: list[str]):
    """Returns credentials, renews them or creates new ones if necessary"""

    path = _get_path()
    token_file = os.path.join(path, token_file)
    client_secret_file = os.path.join(path, client_secret_file)

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
    """Returns credentials without using a token file"""

    path = _get_path()
    client_secret_file = os.path.join(path, client_secret_file)

    try:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
        creds = flow.run_local_server(port=0)

        return creds

    except Exception as e:
        print(f"An error occured: {e}")
