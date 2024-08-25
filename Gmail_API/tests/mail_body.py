import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_message_body(message):
    """Extracts the body of the message."""
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                body = part['body']['data']
                body_decoded = base64.urlsafe_b64decode(body.encode('ASCII')).decode('utf-8')
                return body_decoded
            elif part['mimeType'] == 'text/html':
                body = part['body']['data']
                body_decoded = base64.urlsafe_b64decode(body.encode('ASCII')).decode('utf-8')
                return body_decoded
    else:
        body = message['payload']['body']['data']
        body_decoded = base64.urlsafe_b64decode(body.encode('ASCII')).decode('utf-8')
        return body_decoded
    return "No plain text or HTML content found."

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)

        # Call the Gmail API
        '''results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
        else:
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                msg_str = get_message_body(msg)
                print(msg_str)'''

        msg = service.users().messages().get(userId='me', id='19060653c2e68bd7').execute()
        msg_str = get_message_body(msg)
        print(repr(msg_str))

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()
