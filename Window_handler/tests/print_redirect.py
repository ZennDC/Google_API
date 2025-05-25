import sys
import curses

class StdoutRedirector:
    def __init__(self, process_window):
        self.process_window = process_window

    def write(self, text):
        if text.strip():  # Avoid printing blank lines
            self.process_window.print(text)

    def flush(self):
        pass  # Needed to satisfy Python's expectations of stdout

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
        self.win.addstr(self.line, 1, string.strip())
        self.line += 1
        self.win.noutrefresh()

    def refresh(self):
        self.win.noutrefresh()

def main(stdscr):
    curses.curs_set(0)
    height, width = stdscr.getmaxyx()
    out_win = ProcessWindow(height - 2, width - 2, 1, 1)

    sys.stdout = StdoutRedirector(out_win)  # Redirect all print calls

    for i in range(10):
        print(f"Line {i}")
        curses.doupdate()
        curses.napms(300)

    stdscr.getch()  # Wait for keypress

    sys.stdout = sys.__stdout__  # Restore original stdout when done

curses.wrapper(main)
