"""Text entry: types an answer line by line with human-like timing.

This is the project's typing logic. The only change from the original standalone typer is that its failsafe
is replaced by the app's Cancel button: every keystroke and every pause checks `cancel_event`, and
cancelling raises `Cancelled`.
"""

import logging
import random

from pynput.keyboard import Controller, Key

kb = Controller()

log = logging.getLogger(__name__)

# --- Behavior tuning ---
MIN_WPM, MAX_WPM = 10, 50
WORD_PAUSE_RANGE = (0.5, 1.2)
PAUSE_EVERY_N_LINES = 4
PAUSE_DURATION = 5
TYPO_PROBABILITY = 0.015
BACKSPACE_DELAY = 0.15
LINE_DELAY_RANGE = (0.3, 0.9)
MAX_LINE_LEN = 300


class Cancelled(Exception):
    """Raised when the user cancels typing from the app."""


class Typer:
    """One typing run. `cancel_event` is a threading.Event; `on_progress(n)` gets the count of
    answer characters typed so far (typos and their corrections are not counted)."""

    def __init__(self, cancel_event, on_progress=lambda n: None):
        self.cancel_event = cancel_event
        self.on_progress = on_progress
        self.progress = 0

    # --- replaces the failsafe ---
    def check_cancel(self):
        if self.cancel_event.is_set():
            raise Cancelled()

    def sleep(self, seconds):
        if self.cancel_event.wait(seconds):
            raise Cancelled()

    def type_char(self, ch):
        self.check_cancel()
        kb.type(ch)

    def press_key(self, key):
        self.check_cancel()
        kb.press(key)
        kb.release(key)

    # --- Main typing routine ---
    def type_code(self, lines):

        indent_stack = []
        line_count = 0

        log.debug(f"Typing {len(lines)} lines")

        # A one-line answer (e.g. a single word) is typed without the
        # trailing space and Enter, so it doesn't submit or add a new line.
        typed_lines = [
            line
            for line in lines
            if line.strip()
            and len(line.strip()) <= MAX_LINE_LEN
            and not line.strip().startswith(("#IS", "#IE"))
        ]
        single_line = len(typed_lines) == 1

        for line in lines:

            if not line.strip():
                continue

            if len(line.strip()) > MAX_LINE_LEN:
                log.warning(
                    f"Skipped line longer than {MAX_LINE_LEN} chars: {line[:80]}..."
                )
                continue

            clean_line = line.strip()

            # --- Indentation markers ---
            if clean_line.startswith("#IS"):
                indent_stack.append(clean_line)
                continue

            elif clean_line.startswith("#IE"):
                if not indent_stack:
                    log.warning(f"Unmatched {clean_line}, ignoring")

                if indent_stack:
                    indent_stack.pop()
                    self.press_key(Key.backspace)
                    self.sleep(0.25)
                continue

            clean_line = line.strip() if single_line else line.lstrip()

            word_buffer = ""
            char_count = 0

            # --- Character typing ---
            for ch in clean_line:

                char_count += 1  # noqa: SIM113

                # Random typo
                if random.random() < TYPO_PROBABILITY and ch.isalpha():

                    wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")

                    self.type_char(wrong_char)

                    self.sleep(random.uniform(0.05, 0.2))

                    self.press_key(Key.backspace)

                    self.sleep(BACKSPACE_DELAY)

                self.type_char(ch)

                self.progress += 1
                self.on_progress(self.progress)

                word_buffer += ch

                self.sleep(delay_for_char(ch))

                # Word pause
                if ch in (" ", "\t"):

                    if word_buffer.strip():
                        self.sleep(random.uniform(*WORD_PAUSE_RANGE))

                    word_buffer = ""

                if char_count > MAX_LINE_LEN:
                    break

            line_count += 1

            if single_line:
                continue

            # End line
            self.type_char(" ")

            self.sleep(0.001)

            self.press_key(Key.enter)

            self.sleep(random.uniform(*LINE_DELAY_RANGE))

            if line_count % PAUSE_EVERY_N_LINES == 0:
                self.sleep(PAUSE_DURATION)

        if not single_line:
            self.press_key(Key.enter)

        if indent_stack:
            log.warning(f"Unclosed indent markers: {indent_stack}")

        log.debug(f"Typed {line_count} lines")


# --- Human-like delay ---
def delay_for_char(ch):
    wpm = random.uniform(MIN_WPM, MAX_WPM)
    cps = (wpm * 5) / 60
    base = 1 / cps

    if ch in ".!?":
        return base * random.uniform(2.0, 2.8)

    if ch in ",;:":
        return base * random.uniform(1.5, 2.0)

    if ch in "()[]{}\"'":
        return base * random.uniform(1.2, 1.7)

    if ch == " ":
        return base * random.uniform(1.0, 1.4)

    return base * random.uniform(0.7, 1.1)


def answer_length(lines):
    """Number of answer characters type_code will type for these lines (for the progress bar)."""
    typed = [
        line
        for line in lines
        if line.strip()
        and len(line.strip()) <= MAX_LINE_LEN
        and not line.strip().startswith(("#IS", "#IE"))
    ]
    if len(typed) == 1:
        return len(typed[0].strip())
    return sum(len(line.lstrip()) for line in typed)
