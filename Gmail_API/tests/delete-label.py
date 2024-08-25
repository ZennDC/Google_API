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

        # Remove the label if it exists
        label_name = 'Example Label'  # Replace with your label name
        if label_exists(service, label_name):
            remove_label(service, label_name)
            print(f'Label "{label_name}" removed successfully.')
        else:
            print(f'Label "{label_name}" does not exist.')

    except HttpError as error:
        print(f'An error occurred: {error}')

def label_exists(service, label_name):
    """Check if a label already exists."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    return any(label['name'] == label_name for label in labels)

def remove_label(service, label_name):
    """Remove a label."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label_id = [label['id'] for label in labels if label['name'] == label_name][0]
    service.users().labels().delete(userId='me', id=label_id).execute()

if __name__ == '__main__':
    main()
