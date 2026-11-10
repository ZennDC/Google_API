from datetime import datetime

import pytz

# Define the Belgian time zone
belgian_tz = pytz.timezone("Europe/Brussels")

# Get the current time in the Belgian time zone
belgian_time = datetime.now(belgian_tz)

print("Current time in Belgium:", belgian_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"))
