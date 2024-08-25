import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']

MAIL_LIST = ['noreply@crewplanner.com', 'noreply@absoluteyou.be', 'no-reply@interimsign.com', 'admin@absoluteyou.be']
LABEL = 'Flexi'

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

        if not label_exists(service, LABEL):
            create_label(service, LABEL)
        else:
            print(f'Label "{LABEL}" already exists.')

        ID = get_label_id(service, LABEL)
        if not ID:
            print('No label id found.')

        # List messages
        messages = get_messages(service, -1)

        if not messages:
            print('No messages found.')
        else:
            i = 0
            for message in messages:
                msg_id = message['id']
                print(f'{i}: Message ID: {msg_id}')
                i = i + 1
                # Get the message details
                msg = service.users().messages().get(userId='me', id=msg_id).execute()

                # Get the sender's email address
                sender = None
                sender_mail = None
                for header in msg['payload']['headers']:
                    if header['name'] == 'From':
                        sender = header['value']
                        start_idx = sender.find('<')
                        end_idx = sender.find('>', start_idx)
                        if start_idx != -1 and end_idx != -1:
                            sender_mail = sender[start_idx+1:end_idx]
                        elif start_idx == end_idx == -1:
                            sender_mail = sender

                if sender_mail in MAIL_LIST:
                    print(f'Sender found: {sender}')
                    modify_request_body = {
                    'addLabelIds': [ID]
                    }

                    modified_msg = service.users().messages().modify(userId='me', id=msg_id, body=modify_request_body).execute()
                    print(f'Message with ID {msg_id} successfully labeled.')

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

def get_label_id(service, label_name):
    """Get the id of a label in the user's mailbox."""
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    if not labels:
        print('No labels found.')
    else:
        for label in labels:
            if label['name'] == label_name:
                id = label['id']
                return id
        else:
            print(f'Label {label_name} does not exist.')

def get_messages(service, amount):
    """Return an amount of messages."""
    if amount > 500:
        print('Amount is to high.')
        return
    elif amount == -1:
        messages = []
        next_page_token = None

        while True:
            response = service.users().messages().list(userId='me', pageToken=next_page_token).execute()
            if 'messages' in response:
                messages.extend(response['messages'])
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return messages

    else:
        results = service.users().messages().list(userId='me', maxResults=amount).execute()
        messages = results.get('messages', [])
        return messages

if __name__ == '__main__':
    main()
