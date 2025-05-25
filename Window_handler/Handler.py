import curses
import time
import threading

class WindowHandler:
    class ProcessWindow:
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
        def __init__(self):
            self.data = None  # Placeholder for data, to be set by the main application

        def resetIdData(self):
            pass  # Placeholder for resetting ID data

        def getNextId(self):
            pass  # Placeholder for getting the next ID

        def getMessageTimestamp(self, id):
            pass  # Placeholder for getting the timestamp of a message by ID

    def __init__(self):
        self.out_win = None
        self.in_win = None

    def run(self):
        curses.wrapper(self.main)

    def print(self, string: str):
        timestamp = time.strftime('%H:%M:%S')
        msg = f"[{timestamp}] {string}\n"
        self.out_win.print(msg)
        self.out_win.noutrefresh()
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
        self.out_win = self.ProcessWindow(height - 2, mid_x - 2, 1, 1)
        self.in_win = curses.newwin(height - 2, width - mid_x - 3, 1, mid_x + 1)

        self.out_win.scrollok(True)
        self.in_win.scrollok(True)

    def main(self, fn: function, stdscr: curses.window):
        curses.curs_set(1)  # Set the cursor to visible
        curses.echo()  # Enable echoing of typed characters

        self.draw_border(stdscr)
        self.create_subwindows(stdscr)

        # Initial buffered draw
        self.out_win.noutrefresh()
        self.in_win.noutrefresh()
        curses.doupdate()

        threading.Thread(target=fn).start()

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
            