from Google_API.OAuth import get_credentials
from Google_API.Google_calender_API.Handlers import CalendarHandler
from Google_API.Google_calender_API.Objects import CalendarList

from googleapiclient.discovery import build

def share_calendar(service, calendar_id: str, email: str, role: str):
    """Share the calendar with another user."""
    rule = {
        'scope': {
            'type': 'user',
            'value': email
        },
        'role': role
    }
    
    try:
        acl_rule = service.acl().insert(calendarId=calendar_id, body=rule).execute()
        print(f"Successfully shared calendar with {email}.")
        print(f"ACL Rule: {acl_rule}")
    except Exception as error:
        print(f"An error occurred: {error}")

def get_user_info(creds):
    """Retrieves the user's profile information (email, etc.) using the token."""
    try:
        # Build the OAuth2 service
        oauth2_service = build('oauth2', 'v2', credentials=creds)
        
        # Get the user info
        user_info = oauth2_service.userinfo().get().execute()
        
        # Extract email from the user info
        email = user_info.get('email')
        return email
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


CLIENT_SECRET = 'client_secret.json'
SCOPES = ["https://www.googleapis.com/auth/calendar"]

creds_owner = get_credentials("token.json", CLIENT_SECRET, SCOPES)
creds_adder = get_credentials("other_token.json", CLIENT_SECRET, SCOPES)

service_owner = build("calendar", "v3", credentials=creds_owner)
service_adder = build("calendar", "v3", credentials=creds_adder)

handler_owner = CalendarHandler(service_owner)
handler_adder = CalendarHandler(service_adder)

calendars: list[dict] = handler_owner.list_all_calendars()
ref = {}
index = 0
print("Choose the calendar to share:")
for calendar in calendars:
    index += 1
    ref[index] = calendar
    print(f"{index}: {calendar.get('summary')}")

while True:
    choice = input("Number: ")
    try:
        num = int(choice)
    except ValueError:
        print(f"Not a number: {choice}")
        continue
    if not 0 < num <= index:
        print(f"Number out of range: {num}")
        continue

    break

print("What is the role of the user:\n1: reader\n2: writer\n3: owner")
role_ref = {1: "reader", 2: "writer", 3: "owner"}

while True:
    choice = input("Number: ")
    try:
        rnum = int(choice)
    except ValueError:
        print(f"Not a number: {choice}")
        continue
    if not 0 < rnum <= 3:
        print(f"Number out of range: {rnum}")
        continue

    break

calendar: dict = ref[num]
email = get_user_info(creds_adder)
share_calendar(service_owner, calendar.get("id"), email, role_ref[rnum])

handler_adder.add_existing_calendar({"id": calendar.get("id")})