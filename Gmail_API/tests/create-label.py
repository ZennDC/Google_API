import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.labels']

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

        # Create a new label if it doesn't already exist
        label_name = 'Example Label'  # Replace with your label name
        if not label_exists(service, label_name):
            create_label(service, label_name)
        else:
            print(f'Label "{label_name}" already exists.')

    except HttpError as error:
        print(f'An error occurred: {error}')

def label_exists(service, label_name):
    """Check if a label already exists."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    return any(label['name'] == label_name for label in labels)

def create_label(service, label_name):
    """Create a new label."""
    label = {'name': label_name}
    service.users().labels().create(userId='me', body=label).execute()
    print(f'Label "{label_name}" created successfully.')

if __name__ == '__main__':
    main()
