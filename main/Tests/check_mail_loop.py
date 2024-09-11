import asyncio

from googleapiclient.discovery import build

from OAuth.Google_Credentials import get_credentials as getCreds
from Google_API.Gmail_API.Handlers import MessageHandler

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']

class Data:
    def __init__(self) -> None:
        self.lastId = None
        self.lastTimestamp = None
        self.labelId = None
        self.lock = asyncio.Lock()


async def check_mail(handler: MessageHandler, data: Data):
    async with data.lock:
        messages = []

        handler.resetIdData()
        newId = id = handler.getNextId()
        newTimestamp = timestamp = handler.getMessageTimestamp(newId)

        if timestamp > data.lastTimestamp:
            while True:
                if not ((timestamp < data.lastTimestamp) or (id == data.lastId)):
                    messages.append(id)

                    id = handler.getNextId()
                    timestamp = handler.getMessageTimestamp(id)
                else:
                    break

        data.lastId = newId
        data.lastTimestamp = newTimestamp
            
        print(messages)


async def main():
    lock = asyncio.Lock()

    creds = getCreds("token.json", "credentials.json", SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    handler = MessageHandler(service)

    data = Data()

    data.lastId = handler.getNextId()
    data.lastTimestamp = handler.getMessageTimestamp(data.lastId)

    while True:
        asyncio.create_task(check_mail(handler, data))
        await asyncio.sleep(30)

asyncio.run(main())