import os.path
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_email_timestamps(creds):
    service = build('gmail', 'v1', credentials=creds)
    
    # Call the Gmail API to fetch the list of messages
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    
    timestamps = []
    
    if not messages:
        print('No messages found.')
    else:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            # Extract the timestamp from the internalDate field
            timestamp_ms = int(msg['internalDate'])
            # Convert milliseconds since epoch to datetime
            timestamp = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
            timestamps.append(timestamp)
    
    return timestamps

def main():
    creds = authenticate_gmail()
    timestamps = get_email_timestamps(creds)
    for timestamp in timestamps:
        print(timestamp)

if __name__ == '__main__':
    main()
