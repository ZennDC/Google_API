import sys
import curses
import time
import threading


class _StdoutRedirector:
    def __init__(self, window_handler: 'WindowHandler'):
        self.window_handler = window_handler

    def write(self, text: str):
        if text.strip():  # Avoid printing blank lines
            self.window_handler.print(text)

    def flush(self):
        pass  # Needed to satisfy Python's expectations of stdout

class _ProcessWindow:
        def __init__(self, nlines, ncols, begin_y, begin_x):
            self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
            self.line = 0
            self.max_y = nlines
            self.win.scrollok(True)

        def print(self, string):
            if self.line >= self.max_y - 1:
                self.win.scroll()
                self.line = self.max_y - 2

            self.win.addstr(self.line, 1, string)
            self.line += 1

        def scrollok(self, bool):
            self.win.scrollok(bool)

        def noutrefresh(self):
            self.win.noutrefresh()

        def getmaxyx(self):
            return self.win.getmaxyx()

        def addstr(self, *args, **kwargs):
            self.win.addstr(*args, **kwargs)

        def addch(self, *args, **kwargs):
            self.win.addch(*args, **kwargs)

        def move(self, *args, **kwargs):
            self.win.move(*args, **kwargs)

        def clrtoeol(self):
            self.win.clrtoeol()

        def resetIdData(self):
            pass  # Placeholder for resetting ID data

        def getNextId(self):
            pass  # Placeholder for getting the next ID

        def getMessageTimestamp(self, id):
            pass  # Placeholder for getting the timestamp of a message by ID


class WindowHandler:
    def __init__(self):
        self.main_process_tread = None
        self.initialized = False

    def run(self, fn: callable, args: tuple = ()):
        self.main_process_tread = threading.Thread(target=fn, args=args)
        threading.Thread(target=fn, args=args).start()
        curses.wrapper(self.main)

    def start_after_initialized(self):
        while not self.initialized:
            time.sleep(0.1)
        self.main_process_tread.start()

    def print(self, string: str):
        timestamp = time.strftime('%H:%M:%S')
        msg = f"[{timestamp}] {string}\n"
        self.out_win.print(msg)
        self.out_win.noutrefresh()
        self.in_win.noutrefresh()
        curses.doupdate()

    def draw_border(self, win: curses.window):
        height, width = win.getmaxyx()
        mid_x = width // 2

        # Top and bottom horizontal lines
        for x in range(1, width - 1):
            win.addch(0, x, curses.ACS_HLINE)
            win.addch(height - 1, x, curses.ACS_HLINE)

        # Left, right and middle vertical lines
        for y in range(1, height - 1):
            win.addch(y, 0, curses.ACS_VLINE)
            win.addch(y, width - 2, curses.ACS_VLINE)
            win.addch(y, mid_x, curses.ACS_VLINE)
            win.addch(y, mid_x - 1, curses.ACS_VLINE)

        # Corners
        win.addch(0, 0, curses.ACS_ULCORNER)
        win.addch(0, mid_x - 1, curses.ACS_URCORNER)
        win.addch(height - 1, 0, curses.ACS_LLCORNER)
        win.addch(height - 1, mid_x - 1, curses.ACS_LRCORNER)

        win.addch(0, mid_x, curses.ACS_ULCORNER)
        win.addch(0, width - 2, curses.ACS_URCORNER)
        win.addch(height - 1, mid_x, curses.ACS_LLCORNER)
        win.addch(height - 1, width - 2, curses.ACS_LRCORNER)

        # Titles
        win.addstr(0, 2, " Real-time Output ")
        win.addstr(0, width - mid_x + 2, " User Input ")

        # Apply changes
        win.refresh()

    def create_subwindows(self, stdscr: curses.window):
        height, width = stdscr.getmaxyx()
        mid_x = width // 2

        # Create subwindows for output and input
        self.out_win = _ProcessWindow(height - 2, mid_x - 2, 1, 1)
        self.in_win = curses.newwin(height - 2, width - mid_x - 3, 1, mid_x + 1)

        self.out_win.scrollok(True)
        self.in_win.scrollok(True)

    def main(self, stdscr: curses.window):
        curses.curs_set(1)  # Set the cursor to visible
        curses.echo()  # Enable echoing of typed characters

        self.draw_border(stdscr)
        self.create_subwindows(stdscr)

        # Initial buffered draw
        self.out_win.noutrefresh()
        self.in_win.noutrefresh()
        curses.doupdate()

        sys.stdout = _StdoutRedirector(self)  # Redirect all print calls

        self.initialized = True

        try:
            while True:
                self.in_win.addstr(0, 1, "Command: ")
                self.in_win.move(0, 11)
                self.in_win.clrtoeol()

                self.in_win.noutrefresh()
                curses.doupdate()

                cmd = self.in_win.getstr(0, 11, 30).decode()

                if cmd.strip().lower() == "quit":
                    break

                self.out_win.print(f"[INPUT] {cmd}\n")
                
                self.out_win.noutrefresh()
                curses.doupdate()
        finally:
            curses.endwin()

if __name__ == "__main__":
    pass