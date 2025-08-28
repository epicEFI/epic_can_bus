#!/usr/bin/env python3
import sys
import argparse
import time
import json
import curses
from pathlib import Path

# Import EpicECU helper
try:
    from EpicECU import can_socket, get_variable
except Exception:
    # allow running from repo root
    sys.path.append(str(Path(__file__).resolve().parent))
    from EpicECU import can_socket, get_variable

VAR_JSON_PATH = Path(__file__).resolve().parents[2] / 'variables.json'

class AppState:
    def __init__(self, iface: str, ecu: int, rate_hz: float):
        self.iface = iface
        self.ecu = ecu
        self.rate_hz = max(0.5, min(rate_hz, 50.0))
        self.polling = True
        self.filter_text = ''
        self.selected = []  # list of (name, hash, source)
        self.values = {}     # hash -> (value, ts)
        self.error = ''
        self.focus = 'selector'  # selector | values | search
        self.selector_idx = 0
        self.values_idx = 0
        self.catalog = []   # list of dict {name, hash, source}
        self.sock = None
        # pagination sizes (rows visible); updated by draw functions each frame
        self.selector_page_rows = 10
        self.values_page_rows = 10
        # source filter: 'both' | 'config' | 'output'
        self.source_mode = 'both'
        # search edit state
        self.filter_cursor = 0  # insertion cursor within filter_text

    def toggle_polling(self):
        self.polling = not self.polling

    def bump_rate(self, delta: float):
        self.rate_hz = max(0.5, min(self.rate_hz + delta, 50.0))

    def set_error(self, msg: str):
        self.error = msg

    def clear_error(self):
        self.error = ''

    def set_ecu(self, ecu: int):
        self.ecu = max(0, min(ecu, 15))

    def filtered_catalog(self):
        items = self.catalog
        # source filter
        if self.source_mode != 'both':
            items = [it for it in items if it.get('source') == self.source_mode]
        # text filter
        if not self.filter_text:
            return items
        t = self.filter_text.lower()
        return [it for it in items if t in it['name'].lower()]

    def add_selected(self, item):
        if item not in self.selected:
            self.selected.append(item)

    def remove_selected_at(self, idx: int):
        if 0 <= idx < len(self.selected):
            self.selected.pop(idx)

    def clear_selected(self):
        self.selected.clear()


def load_variables(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        # normalize
        out = []
        for it in data:
            out.append({
                'name': it.get('name', ''),
                'hash': int(it.get('hash', 0)),
                'source': it.get('source', '')
            })
        return out
    except Exception as e:
        return []


def draw_header(win, st: AppState, width):
    win.erase()
    h, w = win.getmaxyx()
    width = min(width, w)
    poll_txt = 'ON' if st.polling else 'OFF'
    msg = f'iface={st.iface}  ECU={st.ecu}  Poll={poll_txt}  Rate={st.rate_hz:.1f}Hz'
    if st.error:
        msg += f'  ERROR: {st.error}'
    help_txt = ' [p]oll  [+/-] rate  [e]cu  [Tab] focus  [Space] select  [f]ilter source  [q]uit'
    try:
        win.addnstr(0, 0, msg.ljust(width), width, curses.color_pair(3) | curses.A_BOLD)
        if h > 1:
            win.addnstr(1, 0, help_txt.ljust(width), width, curses.color_pair(1))
    except curses.error:
        pass
    win.noutrefresh()


def draw_selector(win, st: AppState, height, width):
    win.erase()
    win.bkgd(' ', curses.color_pair(1))
    win.box()
    items = st.filtered_catalog()
    inner_w = max(1, width - 2)
    inner_h = max(1, height - 2)
    # Search line
    # Render filter with cursor position
    cursor = max(0, min(st.filter_cursor, len(st.filter_text)))
    visible = st.filter_text
    search = f'Filter: {visible}'
    search_attr = curses.color_pair(5) if st.focus == 'search' else curses.color_pair(1)
    try:
        win.addnstr(1, 1, search.ljust(inner_w), inner_w, search_attr)
        if st.focus == 'search':
            # place a visible cursor; we can't move terminal cursor in noutrefresh easily, so draw a block
            label_len = len('Filter: ')
            cx = 1 + label_len + cursor
            if cx < inner_w + 1:
                try:
                    win.addnstr(1, cx, (visible[cursor:cursor+1] or ' ').ljust(1), 1, curses.color_pair(5) | curses.A_REVERSE)
                except curses.error:
                    pass
    except curses.error:
        pass
    # Header
    try:
        win.addnstr(2, 1, 'Select variables:'.ljust(inner_w), inner_w, curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass
    # List (start at row 3 inside box)
    view = items
    # Ensure selector index remains valid against current filtered list
    if len(view) == 0:
        st.selector_idx = 0
    else:
        if st.selector_idx >= len(view):
            st.selector_idx = len(view) - 1
        if st.selector_idx < 0:
            st.selector_idx = 0
    list_space = max(0, inner_h - 3)
    st.selector_page_rows = max(1, list_space)
    # keep cursor near middle when possible
    if st.selector_page_rows > 0:
        start = max(0, st.selector_idx - (st.selector_page_rows // 2))
        max_start = max(0, len(view) - st.selector_page_rows)
        start = min(start, max_start)
    else:
        start = 0
    end = min(len(view), start + st.selector_page_rows)
    row = 3
    for i in range(start, end):
        it = view[i]
        checked = '[x]' if it in st.selected else '[ ]'
        line = f'{checked} {it["name"]:<32} {it["source"]:<6} hash={it["hash"]}'
        is_cursor = (st.focus == 'selector' and i == st.selector_idx)
        attr = curses.color_pair(2) | curses.A_BOLD if is_cursor else curses.color_pair(1)
        try:
            win.addnstr(row, 1, line.ljust(inner_w), inner_w, attr)
        except curses.error:
            pass
        row += 1
    win.noutrefresh()


def draw_values(win, st: AppState, height, width):
    win.erase()
    win.bkgd(' ', curses.color_pair(1))
    win.box()
    inner_w = max(1, width - 2)
    inner_h = max(1, height - 2)
    try:
        win.addnstr(1, 1, 'Live values:'.ljust(inner_w), inner_w, curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass
    page_rows = max(1, inner_h - 2)
    st.values_page_rows = page_rows
    # keep cursor near middle when possible
    if st.values_page_rows > 0:
        start = max(0, st.values_idx - (st.values_page_rows // 2))
        max_start = max(0, len(st.selected) - st.values_page_rows)
        start = min(start, max_start)
    else:
        start = 0
    end = min(len(st.selected), start + st.values_page_rows)
    row = 2
    now = time.time()
    for i in range(start, end):
        it = st.selected[i]
        h = int(it['hash'])
        v, ts = st.values.get(h, ('—', 0))
        age = f'{int(now - ts)}s' if ts else '—'
        val_txt = f'{v:.3f}' if isinstance(v, float) else str(v)
        line = f'{it["name"]:<32} {val_txt:>12}  {age:>4}  hash={h}'
        is_cursor = (st.focus == 'values' and i == st.values_idx)
        attr = curses.color_pair(2) | curses.A_BOLD if is_cursor else curses.color_pair(1)
        try:
            win.addnstr(row, 1, line.ljust(inner_w), inner_w, attr)
        except curses.error:
            pass
        row += 1
    win.noutrefresh()


def handle_key(stdscr, st: AppState, ch):
    # Global exit
    if ch in (ord('q'), ord('Q')):
        return False
    # Search mode: only edit/filter keys + Tab allowed
    if st.focus == 'search':
        # Ignore service/special keys so they don't insert garbage
        service_keys = (
            curses.KEY_UP, curses.KEY_PPAGE, curses.KEY_NPAGE,
            curses.KEY_HOME, curses.KEY_END, curses.KEY_IC, curses.KEY_DC
        )
        if ch in service_keys:
            return True
        # Function keys (F1..F12) if available
        try:
            if ch >= curses.KEY_F0 and ch <= curses.KEY_F12:
                return True
        except Exception:
            pass
        if ch == curses.KEY_BTAB:
            # Shift-Tab from search goes to live values if any are selected
            if len(st.selected) > 0:
                st.focus = 'values'
            return True
        if ch == curses.KEY_DOWN:
            # Move from filter box to the selector list below only if there are items
            filtered = st.filtered_catalog()
            if len(filtered) > 0:
                # clamp selection into range so highlight is visible
                if st.selector_idx >= len(filtered):
                    st.selector_idx = len(filtered) - 1
                if st.selector_idx < 0:
                    st.selector_idx = 0
                st.focus = 'selector'
            return True
        if ch == curses.KEY_LEFT:
            st.filter_cursor = max(0, st.filter_cursor - 1)
            return True
        if ch == curses.KEY_RIGHT:
            st.filter_cursor = min(len(st.filter_text), st.filter_cursor + 1)
            return True
        if ch in (ord('\t'), 9):
            # From search: prefer selector if it has items, otherwise go to values if there are selected items.
            filtered = st.filtered_catalog()
            if len(filtered) > 0:
                if st.selector_idx >= len(filtered):
                    st.selector_idx = len(filtered) - 1
                if st.selector_idx < 0:
                    st.selector_idx = 0
                st.focus = 'selector'
            elif len(st.selected) > 0:
                st.focus = 'values'
            # else remain in search
            return True
        if ch in (27,):  # ESC clears filter
            st.filter_text = ''
            st.filter_cursor = 0
            return True
        if ch in (10, 13):  # Enter keeps filter
            return True
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if st.filter_cursor > 0:
                st.filter_text = st.filter_text[:st.filter_cursor-1] + st.filter_text[st.filter_cursor:]
                st.filter_cursor -= 1
            return True
        # Printable
        try:
            c = chr(ch)
        except Exception:
            c = ''
        if c and (c.isalnum() or c in '._-'):
            st.filter_text = st.filter_text[:st.filter_cursor] + c + st.filter_text[st.filter_cursor:]
            st.filter_cursor += 1
        return True
    # Global navigation (not in search)
    if ch in (ord('\t'), 9):  # Tab cycles: search -> selector -> values -> search
        if st.focus == 'selector':
            # selector -> values (only if any selected), else -> search
            st.focus = 'values' if len(st.selected) > 0 else 'search'
        elif st.focus == 'values':
            st.focus = 'search'
        else:  # from search handled earlier; here ensure consistent fallback
            if len(st.filtered_catalog()) > 0:
                st.focus = 'selector'
        return True
    # Shift-Tab (KEY_BTAB) cycles in reverse
    if ch == curses.KEY_BTAB:
        if st.focus == 'selector':
            st.focus = 'search'
        elif st.focus == 'values':
            # values -> selector if any items in selector, else -> search
            st.focus = 'selector' if len(st.filtered_catalog()) > 0 else 'search'
        else:  # from search: prefer values if non-empty, else selector if non-empty, else stay
            if len(st.selected) > 0:
                st.focus = 'values'
            elif len(st.filtered_catalog()) > 0:
                st.focus = 'selector'
        return True
    if ch in (ord('p'), ord('P')):
        st.toggle_polling()
        return True
    if ch in (ord('f'), ord('F')):
        # Cycle source filter: both -> config -> output -> both
        st.source_mode = 'config' if st.source_mode == 'both' else ('output' if st.source_mode == 'config' else 'both')
        # Reset selector index to keep view sane
        st.selector_idx = 0
        return True
    if ch in (ord('+'), ord('=')):
        st.bump_rate(+0.5)
        return True
    if ch in (ord('-'), ord('_')):
        st.bump_rate(-0.5)
        return True
    if ch in (ord('e'), ord('E')):
        # simple prompt for ECU id
        curses.echo()
        try:
            stdscr.addstr(curses.LINES - 1, 0, 'Enter ECU id (0..15): '.ljust(curses.COLS), curses.color_pair(1))
            val = stdscr.getstr(curses.LINES - 1, 22, 3).decode('utf-8')
        finally:
            curses.noecho()
        try:
            st.set_ecu(int(val, 0))
            st.clear_error()
        except Exception:
            st.set_error('invalid ECU id')
        return True
    if st.focus == 'selector':
        items = st.filtered_catalog()
        if ch == curses.KEY_UP:
            st.selector_idx = max(0, st.selector_idx - 1)
            return True
        if ch == curses.KEY_DOWN:
            st.selector_idx = min(max(0, len(items) - 1), st.selector_idx + 1)
            return True
        if ch == curses.KEY_NPAGE:  # Page Down
            st.selector_idx = min(max(0, len(items) - 1), st.selector_idx + st.selector_page_rows)
            return True
        if ch == curses.KEY_PPAGE:  # Page Up
            st.selector_idx = max(0, st.selector_idx - st.selector_page_rows)
            return True
        if ch == curses.KEY_END:
            st.selector_idx = max(0, len(items) - 1)
            return True
        if ch == curses.KEY_HOME:
            st.selector_idx = 0
            return True
        if ch == ord(' '):
            if 0 <= st.selector_idx < len(items):
                it = items[st.selector_idx]
                if it in st.selected:
                    st.selected.remove(it)
                else:
                    st.add_selected(it)
            return True
    if st.focus == 'values':
        if ch == curses.KEY_UP:
            st.values_idx = max(0, st.values_idx - 1)
            return True
        if ch == curses.KEY_DOWN:
            st.values_idx = min(max(0, len(st.selected) - 1), st.values_idx + 1)
            return True
        if ch == curses.KEY_NPAGE:
            st.values_idx = min(max(0, len(st.selected) - 1), st.values_idx + st.values_page_rows)
            return True
        if ch == curses.KEY_PPAGE:
            st.values_idx = max(0, st.values_idx - st.values_page_rows)
            return True
        if ch == curses.KEY_END:
            st.values_idx = max(0, len(st.selected) - 1)
            return True
        if ch == curses.KEY_HOME:
            st.values_idx = 0
            return True
        if ch in (curses.KEY_DC, 127):  # Delete key (and DEL on some terms)
            st.remove_selected_at(st.values_idx)
            st.values_idx = max(0, min(st.values_idx, len(st.selected) - 1))
            return True
        if ch in (ord('r'), ord('R')):
            st.remove_selected_at(st.values_idx)
            st.values_idx = max(0, min(st.values_idx, len(st.selected) - 1))
            return True
        if ch in (ord('c'), ord('C')):
            st.clear_selected()
            st.values_idx = 0
            return True
    if st.focus == 'search':
        if ch in (curses.KEY_UP, curses.KEY_DOWN):
            return True
        if ch in (10, 13):  # Enter
            return True
        if ch in (27,):  # ESC -> clear
            st.filter_text = ''
            return True
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            st.filter_text = st.filter_text[:-1]
            return True
        try:
            st.filter_text += chr(ch)
        except Exception:
            pass
        return True
    return True


def poll_once(st: AppState):
    if not st.selected or not st.sock:
        return
    for it in st.selected:
        h = int(it['hash'])
        try:
            v = get_variable(st.sock, h, dest=st.ecu)
            st.values[h] = (float(v), time.time())
            st.clear_error()
        except Exception as e:
            st.set_error(str(e))


def run(stdscr, st: AppState):
    curses.curs_set(0)
    # Colors: Norton Commander style (blue background)
    curses.start_color()
    try:
        curses.use_default_colors()
    except Exception:
        pass
    # pair 1: normal (white on blue)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    # pair 2: selection highlight (bright yellow on cyan)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_CYAN)
    # pair 3: header (cyan on blue)
    curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLUE)
    # pair 4: error (red on blue)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLUE)
    # pair 5: search input (black on cyan)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)

    stdscr.bkgd(' ', curses.color_pair(1))
    stdscr.nodelay(True)
    stdscr.timeout(50)

    st.catalog = load_variables(VAR_JSON_PATH)
    try:
        st.sock = can_socket(st.iface)
    except Exception as e:
        st.set_error(f'CAN open failed: {e}')
        st.sock = None

    last_poll = 0.0
    while True:
        height, width = stdscr.getmaxyx()
        header_h = 2
        selector_w = max(40, width // 2)
        selector_h = height - header_h
        values_w = width - selector_w
        values_h = height - header_h

        header_win = curses.newwin(header_h, width, 0, 0)
        selector_win = curses.newwin(selector_h, selector_w, header_h, 0)
        values_win = curses.newwin(values_h, values_w, header_h, selector_w)
        header_win.bkgd(' ', curses.color_pair(1))
        selector_win.bkgd(' ', curses.color_pair(1))
        values_win.bkgd(' ', curses.color_pair(1))

        draw_header(header_win, st, width)
        draw_selector(selector_win, st, selector_h, selector_w)
        draw_values(values_win, st, values_h, values_w)
        curses.doupdate()

        try:
            ch = stdscr.getch()
            if ch != -1:
                if not handle_key(stdscr, st, ch):
                    break
        except KeyboardInterrupt:
            break

        now = time.time()
        if st.polling and (now - last_poll) >= (1.0 / st.rate_hz):
            poll_once(st)
            last_poll = now


def main():
    ap = argparse.ArgumentParser(description='ncurses ECU variable monitor over EPIC CANbus')
    ap.add_argument('--iface', default='can0', help='SocketCAN interface (default: can0)')
    ap.add_argument('--ecu', type=int, default=0, help='ECU address 0..15 (default: 0)')
    ap.add_argument('--rate', type=float, default=10.0, help='Poll rate in Hz (default: 10.0)')
    args = ap.parse_args()

    st = AppState(args.iface, args.ecu, args.rate)
    curses.wrapper(run, st)

if __name__ == '__main__':
    main()
