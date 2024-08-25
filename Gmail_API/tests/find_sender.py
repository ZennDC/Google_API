import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
MAIL_LIST = ['noreply@crewplanner.com', 'noreply@absoluteyou.be', 'no-reply@interimsign.com']

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
        results = service.users().messages().list(userId='me', maxResults=50).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
        else:
            for message in messages:
                msg_id = message['id']
                print(f'Message ID: {msg_id}')

                # Get the message details
                msg = service.users().messages().get(userId='me', id=msg_id).execute()

                # Get the sender's email address
                sender = None
                for header in msg['payload']['headers']:
                    if header['name'] == 'From':
                        sender = header['value']
                        start_idx = sender.find('<') + 1
                        end_idx = sender.find('>', start_idx)
                        if start_idx != -1 and end_idx != -1:
                            sender_mail = sender[start_idx:end_idx]
                        break

                if sender:
                    if sender_mail in MAIL_LIST:
                        print(f'Sender found: {sender}')

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()
