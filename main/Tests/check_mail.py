from OAuth.Google_Credentials import get_credentials as getCreds
from Google_API.Gmail_API.Handlers import MessageHandler

import time

from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']

creds = getCreds("token.json", "credentials.json", SCOPES)

service = build('gmail', 'v1', credentials=creds)

handler = MessageHandler(service)

lastId = handler.getNextId()
lastTimestamp = handler.getMessageTimestamp(lastId)

while True:
    handler.resetIdData()

    newId = handler.getNextId()
    newTimestamp = handler.getMessageTimestamp(newId)

    messages = []
    if newTimestamp > lastTimestamp:
        while True:
            messages.append(newId)
            id = handler.getNextId()
            timestamp = handler.getMessageTimestamp(id)
            if (timestamp < lastTimestamp) or (id == lastId):
                break

        lastId = newId
        lastTimestamp = newTimestamp

    else:
        print('no new messages')

    print(messages)
    time.sleep(60)