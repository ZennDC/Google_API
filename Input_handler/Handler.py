import asyncio
import sys


class InputHandler:
    async def user_input_handler(self):
        loop = asyncio.get_running_loop()
        while True:
            user_input = None
            try:
                await loop.run_in_executor(None, self.clear_input_prompt)
                user_input = await loop.run_in_executor(None, input, 'Enter something: ')
            except asyncio.CancelledError:
                break  # Handle cancellation if necessary
            if user_input is not None:
                self.handle_user_input(user_input)

    def handle_user_input(self, user_input):
        # Process user input here
        self.clear_input_prompt()
        print(f"Received input: {user_input}")

    def clear_input_prompt(self):
        # Clear the input line
        sys.stdout.write('\r\033[K')  # Move cursor up and clear line
        sys.stdout.flush()

    def restore_input_prompt(self):
        # Restore the input prompt
        sys.stdout.write('Enter something: ')
        sys.stdout.flush()

    def printc(self, item):
        self.clear_input_prompt()
        print(item)
        self.restore_input_prompt()
