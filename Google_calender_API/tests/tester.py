from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = Credentials.from_authorized_user_file("token.json", SCOPES)
service = build("calendar", "v3", credentials=creds)


#colors = service.colors().get().execute()

#print(colors)
cals = []
page_token = None
while True:
  calendar_list = service.calendarList().list(pageToken=page_token).execute()
  for calendar_list_entry in calendar_list['items']:
    cals.append(calendar_list_entry)
  page_token = calendar_list.get('nextPageToken')
  if not page_token:
    break

calendar_list_entry = service.calendarList().get(calendarId='7e4ed0e8c1d724a873e00a086e761ba7299e65b0fd2fd5b615e4309b2edb535f@group.calendar.google.com').execute()
# Set custom background and foreground colors
calendar_list_entry['backgroundColor'] = '#FF0000'  # Red background color
calendar_list_entry['foregroundColor'] = '#FFFFFF'  # White foreground color

# Update the calendar list entry with colorRgbFormat set to true
updated_calendar_list_entry = service.calendarList().update(
    calendarId='7e4ed0e8c1d724a873e00a086e761ba7299e65b0fd2fd5b615e4309b2edb535f@group.calendar.google.com',
    body=calendar_list_entry,
    colorRgbFormat=True  # Enable RGB color format
).execute()

# Print the updated calendar list entry details
print(updated_calendar_list_entry)

