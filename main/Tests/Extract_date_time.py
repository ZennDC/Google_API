import re
import asyncio

from googleapiclient.discovery import build

from OAuth.Google_Credentials import get_credentials as getCreds
from Google_API.Gmail_API.Handlers import MessageHandler, LabelHandler

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels']

TIME_DELAY = 30

MAIL_LIST = ['noreply@crewplanner.com', 'noreply@absoluteyou.be', 'no-reply@interimsign.com', 'admin@absoluteyou.be', 'zenn.decraene@gmail.com']
LABEL_ALL = 'Werk'

MAIL_ADDR = ['noreply@crewplanner.com', 'zenn.decraene@gmail.com']
PATTERN = r'\r\n(..) +(\d{1,2} \w+ \d{4}) \| (\d{2}:\d{2} - \d{2}:\d{2})\r\n'
PLANNED_LABEL = 'Ingepland'


class Data:
    def __init__(self) -> None:
        self.lastId = None
        self.lastTimestamp = None
        self.labelId_label_all = None
        self.labelId_planned_label = None
        self.lock = asyncio.Lock()
    

async def async_mail_handler(messageHandler: MessageHandler, labelHandler: LabelHandler, data: Data):
    messages = await get_new_mail(messageHandler, data)

    # Label all work-related messages
    filtered_messages = messageHandler.filterSenders(messages, MAIL_LIST)
    for message_id in filtered_messages:
        labelHandler.add_label_to_message(message_id, data.labelId_label_all)

    # Extract date and time from messages
    filtered_messages = messageHandler.filterSenders(messages, MAIL_ADDR)
    #filtered_messages.append('1905450717abc27a')
    #filtered_messages.append('19060653c2e68bd7')

    for message_id in filtered_messages:
        message_body = messageHandler.getMessageBody(message_id)

        matches = re.findall(PATTERN, message_body)

        if not matches:
            print('No matches found.')
        else:
            labelHandler.add_label_to_message(message_id, data.labelId_planned_label)
            for match in matches:
                print(f"Day: {match[0]}, Date: {match[1]}, Time: {match[2]}")


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

    data.labelId_label_all = lh.get_or_create_label_id(LABEL_ALL)
    data.labelId_planned_label = lh.get_or_create_label_id(PLANNED_LABEL)

    while True:
        asyncio.create_task(async_mail_handler(mh, lh, data))
        await asyncio.sleep(TIME_DELAY)

asyncio.run(main())