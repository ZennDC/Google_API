import asyncio

from googleapiclient.discovery import build

from OAuth.Google_Credentials import get_credentials as getCreds
from Google_API.Gmail_API.Handlers import MessageHandler, LabelHandler

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']
MAIL_LIST = ['noreply@crewplanner.com', 'noreply@absoluteyou.be', 'no-reply@interimsign.com', 'admin@absoluteyou.be', 'zenn.decraene@gmail.com']
LABEL = 'Werk'
TIME_DELAY = 30

class Data:
    def __init__(self) -> None:
        self.lastId = None
        self.lastTimestamp = None
        self.labelId = None
        self.lock = asyncio.Lock()


async def async_mail_handler(messageHandler: MessageHandler, labelHandler: LabelHandler, data: Data):
    messages = await get_new_mail(messageHandler, data)

    filtered_messages = messageHandler.filterSenders(messages, MAIL_LIST)
    for message_id in filtered_messages:
        labelHandler.add_label_to_message(message_id, data.labelId)


async def get_new_mail(handler: MessageHandler, data: Data):
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
        return messages


async def main():
    creds = getCreds("token.json", "credentials.json", SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    mh = MessageHandler(service)
    lh = LabelHandler(service)

    data = Data()
    data.lastId = mh.getNextId()
    data.lastTimestamp = mh.getMessageTimestamp(data.lastId)

    if not lh.label_exists(LABEL):
        lh.create_label(LABEL)
    else:
        print(f'Label "{LABEL}" already exists.')

    data.labelId = lh.get_label_id(LABEL)
    if not data.labelId:
        raise RuntimeError(f"ID for {LABEL} not found")

    while True:
        asyncio.create_task(async_mail_handler(mh, lh, data))
        await asyncio.sleep(TIME_DELAY)

asyncio.run(main())