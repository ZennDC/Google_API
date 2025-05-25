import curses
import threading
import time

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

def background_worker(out_win: ProcessWindow, in_win: curses.window, stop_event):
    while not stop_event.is_set():
        timestamp = time.strftime('%H:%M:%S')
        msg = f"[{timestamp}] Background update {out_win.line + 1}\n"

        out_win.print(msg)

        # Redraw both windows
        out_win.noutrefresh()
        in_win.noutrefresh()
        curses.doupdate()

        time.sleep(1)

def draw_border(win: curses.window):
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

def add_subwindows(stdscr: curses.window):
    height, width = stdscr.getmaxyx()
    mid_x = width // 2

    # Create subwindows for output and input
    out_win = ProcessWindow(height - 2, mid_x - 2, 1, 1)
    in_win = curses.newwin(height - 2, width - mid_x - 3, 1, mid_x + 1)

    out_win.scrollok(True)
    in_win.scrollok(True)

    return out_win, in_win

def main(stdscr: curses.window):
    curses.curs_set(1)  # Set the cursor to visible
    curses.echo()  # Enable echoing of typed characters

    draw_border(stdscr)
    out_win, in_win = add_subwindows(stdscr)

    # Initial buffered draw
    out_win.noutrefresh()
    in_win.noutrefresh()
    curses.doupdate()

    stop_event = threading.Event()
    thread = threading.Thread(target=background_worker, args=(out_win, in_win, stop_event))
    thread.start()

    try:
        while True:
            in_win.addstr(0, 1, "Command: ")
            in_win.move(0, 11)
            in_win.clrtoeol()

            in_win.noutrefresh()
            curses.doupdate()

            cmd = in_win.getstr(0, 11, 30).decode()

            if cmd.strip().lower() == "quit":
                break

            out_win.print(f"[INPUT] {cmd}\n")
            
            out_win.noutrefresh()
            curses.doupdate()
    finally:
        stop_event.set()
        thread.join()

curses.wrapper(main)
