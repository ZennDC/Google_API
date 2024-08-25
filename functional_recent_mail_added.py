import re
import asyncio

from googleapiclient.discovery import build

from Google_API.Login.Credentials import get_credentials as getCreds
from Google_API.Gmail_API.Handlers import MessageHandler, LabelHandler
from Google_API.Google_calender_API.Handlers import EventHandler, CalendarHandler
from Google_API.Google_calender_API.Objects import Calendar, TimedEvent, convert_date

SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.labels', 'https://www.googleapis.com/auth/gmail.readonly', "https://www.googleapis.com/auth/calendar"]

TIME_DELAY = 300

MAIL_LIST = ['noreply@crewplanner.com', 'noreply@absoluteyou.be', 'no-reply@interimsign.com', 'admin@absoluteyou.be']
LABEL_ALL = 'Werk'

MAIL_ADDR = ['noreply@crewplanner.com', 'zenn.decraene@gmail.com']
PATTERN = r'\r\n(..) +(\d{1,2} \w+ \d{4}) \| (\d{2}:\d{2} - \d{2}:\d{2})\r\n\r\n[^\r\n]+?bij\s+([^\r\n]+?)\r\n\r\n([^\r\n]+?)\r\n'
PLANNED_LABEL = 'Ingepland'
CALENDAR_NAME = 'Werk'

RECENT_MAIL_AMOUNT = -1


class Handlers:
        def __init__(self, messageHandler: MessageHandler, labelHandler: LabelHandler, eventHandler: EventHandler, calendarHandler: CalendarHandler) -> None:
            self.messageHandler = messageHandler
            self.labelHandler = labelHandler
            self.eventHandler = eventHandler
            self.calendarHandler = calendarHandler


class Data:
    def __init__(self) -> None:
        self.lastId = None
        self.lastTimestamp = None
        self.labelId_label_all = None
        self.labelId_planned_label = None
        self.work_calendar_id = None
        self.lock = asyncio.Lock()
        self.stopFlag = False
    

async def async_mail_handler(handlers: Handlers, data: Data):
    # Get recent mail
    #messages = await get_new_mail(handlers.messageHandler, data)

    # Get an amount of already received mail
    messages = await get_recent_mail(handlers.messageHandler, data, RECENT_MAIL_AMOUNT)
    data.stopFlag=True

    # Label all work-related messages
    filtered_messages = handlers.messageHandler.filterSenders(messages, MAIL_LIST)
    for message_id in filtered_messages:
        handlers.labelHandler.add_label_to_message(message_id, data.labelId_label_all)
    
    await mail_to_event_handler(handlers, data, messages)

async def mail_to_event_handler(handlers: Handlers, data: Data, messages: list) -> None:

    # Extract date and time from messages
    filtered_messages = handlers.messageHandler.filterSenders(messages, MAIL_ADDR)

    # Test messages
    #filtered_messages.append('1905450717abc27a')
    #filtered_messages.append('19060653c2e68bd7')

    for message_id in filtered_messages:
        message_body = handlers.messageHandler.getMessageBody(message_id)

        matches = re.findall(PATTERN, message_body)

        if not matches:
            print('No matches found.')
        else:
            handlers.labelHandler.add_label_to_message(message_id, data.labelId_planned_label)
            for match in matches:
                day, date, time, place, location = match

                print(f"New event: {place}, {day} {date}, {time}, Location: {location}")
                
                start_date = handlers.eventHandler.convert_date(date)
                start_time, end_time = handlers.eventHandler.convert_time(time)

                if handlers.eventHandler.is_greater(start_time, end_time):
                    end_date = convert_date(start_date, add_day=True, output_format="%d/%m/%Y")
                else:
                    end_date = start_date

                event = TimedEvent(place, start_date, start_time, end_date, end_time, time_format='%H:%M')
                event.location = location

                event_obj = event.build()
                handlers.eventHandler.planEvent(data.work_calendar_id, event_obj)

async def get_new_mail(handler: MessageHandler, data: Data) -> list:
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

async def get_recent_mail(handler: MessageHandler, data: Data, amount: int) -> list:
    async with data.lock:
        print(f"Started gathering {amount} messages")

        handler.resetIdData()
        message_ids = []

        if amount == -1:
            i = 0
            while True:
                id = handler.getNextId()
                if not id:
                    print(f"No more messages to fetch, stopped at {i-1}")
                    break
                else:
                    print(f"Message {i}/{amount}")
                    i += 1
                    message_ids.append(id)
        
        else:        
            for i in range(amount):
                id = handler.getNextId()
                if not id:
                    print(f"No more messages to fetch, stopped at {i-1}")
                    break
                else:
                    print(f"Message {i}/{amount}")
                    message_ids.append(id)
        
        return message_ids


async def main():
    creds = getCreds("token.json", "credentials.json", SCOPES)

    gmail_service = build('gmail', 'v1', credentials=creds)
    gcalendar_service = build("calendar", "v3", credentials=creds)

    mh = MessageHandler(gmail_service)
    lh = LabelHandler(gmail_service)

    eh = EventHandler(gcalendar_service)
    ch = CalendarHandler(gcalendar_service)

    handlers = Handlers(mh, lh, eh, ch)
    data = Data()

    data.lastId = handlers.messageHandler.getNextId()
    data.lastTimestamp = handlers.messageHandler.getMessageTimestamp(data.lastId)

    data.labelId_label_all = handlers.labelHandler.get_or_create_label_id(LABEL_ALL)
    data.labelId_planned_label = handlers.labelHandler.get_or_create_label_id(PLANNED_LABEL)

    id = handlers.calendarHandler.get_calendar_id(CALENDAR_NAME)
    if not id:
        print(f'Creating calendar "{CALENDAR_NAME}".')
        calendar_obj = Calendar(CALENDAR_NAME).build()
        id = handlers.calendarHandler.create_calendar(calendar_obj)
        if id:
            print(f'Calendar "{CALENDAR_NAME}" created.')
        else:
            print(f'A problem occured while createing calendar "{CALENDAR_NAME}".')
    else:
        print(f'Calendar "{CALENDAR_NAME}" already exists.')

    data.work_calendar_id = id

    while not data.stopFlag:
        asyncio.create_task(async_mail_handler(handlers, data))
        await asyncio.sleep(TIME_DELAY)

asyncio.run(main())