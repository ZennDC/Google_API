import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the scope of access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    # Perform the OAuth flow if there are no valid credentials
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')

    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')

    # Print the authorization URL to the terminal
    print('Please go to this URL and finish the authentication: {}'.format(auth_url))

    # After manually opening the URL and authenticating, get the credentials
    code = input('Enter the authorization code: ')
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Use the credentials to create a Gmail API service
    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API to fetch user's labels
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
        print('Labels:')
        for label in labels:
            print(label['name'])

if __name__ == '__main__':
    main()
