import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

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

        # List messages
        results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
        else:
            for message in messages:
                msg_id = message['id']
                print(f'Message ID: {msg_id}')

                # Modify message to add a label
                label_id = 'IMPORTANT'  # Replace with your label ID
                modify_request_body = {
                    'addLabelIds': [label_id]
                }

                modified_msg = service.users().messages().modify(userId='me', id=msg_id, body=modify_request_body).execute()
                print(f'Message with ID {msg_id} successfully labeled.')

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()
