import json
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

tokenf = 'token.json'
credsf = 'credentials.json'

scopes = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']

def scopes_in_token(scopes, tokenf):
    if os.path.exists(tokenf):
        with open(tokenf, 'r') as f:
            data = json.load(f)
            return set(scopes).issubset(set(data.get('scopes', [])))
    return False

def main():
    creds = Credentials.from_authorized_user_file(tokenf, scopes) if os.path.exists(tokenf) else None

    if not scopes_in_token(scopes, tokenf) or not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credsf, scopes)
            creds = flow.run_local_server(port=0)

        with open(tokenf, 'w') as token:
            token.write(creds.to_json())

if __name__ == '__main__':
    main()
