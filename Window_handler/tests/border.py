import curses

def main(stdscr):
    # Get screen height and width
    height, width = stdscr.getmaxyx()

    # Draw a border using ACS characters
    stdscr.border(
        curses.ACS_VLINE, curses.ACS_VLINE,  # left, right
        curses.ACS_HLINE, curses.ACS_HLINE,  # top, bottom
        curses.ACS_ULCORNER, curses.ACS_URCORNER,  # top-left, top-right
        curses.ACS_LLCORNER, curses.ACS_LRCORNER   # bottom-left, bottom-right
    )

    # Display screen size info
    size_info = f"Size: {height}x{width}"
    stdscr.addstr(1, 2, size_info)

    # Refresh to draw everything
    stdscr.refresh()
    stdscr.getch()

curses.wrapper(main)
