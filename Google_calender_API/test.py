from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
# Assuming you've already authenticated and have a `service` object
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = Credentials.from_authorized_user_file("token.json", SCOPES)
service = build('calendar', 'v3', credentials=creds)

# Define the calendar with a colorId
calendar = {
    'summary': 'Sample Calendar with Color',
    'timeZone': 'America/Los_Angeles',
    'colorId': '5'  # Use a predefined colorId (e.g., 5)
}

# Create the calendar
created_calendar = service.calendars().insert(body=calendar).execute()

# Print the created calendar details
print(created_calendar)
