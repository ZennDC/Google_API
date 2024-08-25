import asyncio
import sys

async def main():
    # Start the user input handler as a separate task
    asyncio.create_task(user_input_handler())

    while True:
        clear_input_prompt()
        print('loop restarted')
        restore_input_prompt()
        asyncio.create_task(async_mail_handler(handlers, data))
        await asyncio.sleep(TIME_DELAY)

async def async_mail_handler(handlers, data):
    # Your async mail handling code here
    pass

async def user_input_handler():
    loop = asyncio.get_running_loop()
    while True:
        user_input = None
        try:
            await loop.run_in_executor(None, clear_input_prompt)
            user_input = await loop.run_in_executor(None, input, 'Enter something: ')
        except asyncio.CancelledError:
            break  # Handle cancellation if necessary
        if user_input is not None:
            handle_user_input(user_input)

def handle_user_input(user_input):
    # Process user input here
    clear_input_prompt()
    print(f"Received input: {user_input}")

def clear_input_prompt():
    # Clear the input line
    sys.stdout.write('\r\033[K')  # Move cursor up and clear line
    sys.stdout.flush()

def restore_input_prompt():
    # Restore the input prompt
    sys.stdout.write('Enter something: ')
    sys.stdout.flush()

# Example usage
class Data:
    stopFlag = False

data = Data()  # Define your 'data' object
handlers = []  # Define your 'handlers' object
TIME_DELAY = 10  # Example time delay of 10 seconds

asyncio.run(main())
