import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
        
        messages = []
        next_page_token = None

        while True:
            response = service.users().messages().list(userId='me', pageToken=next_page_token).execute()
            if 'messages' in response:
                messages.extend(response['messages'])
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f'Total messages: {len(messages)}')
        for message in messages:
            print(f'Message ID: {message["id"]}')

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()
