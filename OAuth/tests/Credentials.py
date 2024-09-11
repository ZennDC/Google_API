import json
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as Creds
from google_auth_oauthlib.flow import InstalledAppFlow

def get_credentials(token_file: str, client_secret_file: str, scopes: list[str]):
    """Returns credentials, renews them or creates new ones if necessary"""
    def scopes_in_token(scopes, tokenf):
        if os.path.exists(tokenf):
            with open(tokenf, 'r') as f:
                data = json.load(f)
                return set(scopes).issubset(set(data.get('scopes', [])))
        return False

    creds = Creds.from_authorized_user_file(token_file, scopes) if os.path.exists(token_file) else None

    if not scopes_in_token(scopes, token_file) or not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
        creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return creds