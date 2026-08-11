import platform
import time
import random


MIN_WPM, MAX_WPM = 10, 50
WORD_PAUSE_RANGE = (0.5, 1.2)
PAUSE_EVERY_N_LINES = 4
PAUSE_DURATION = 5
TYPO_PROBABILITY = 0.015
BACKSPACE_DELAY = 0.15
LINE_DELAY_RANGE = (0.3, 0.9)
MAX_LINE_LEN = 300


SYSTEM = platform.system()


if SYSTEM == "Windows":

    import keyboard

elif SYSTEM == "Darwin":

    from pynput.keyboard import Controller, Key

    kb = Controller()

else:

    raise RuntimeError(
        f"Unsupported operating system: {SYSTEM}"
    )


def delay_for_char(ch):

    wpm = random.uniform(
        MIN_WPM,
        MAX_WPM
    )

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


def press_backspace():

    if SYSTEM == "Windows":

        keyboard.send("backspace")

    else:

        kb.press(Key.backspace)
        kb.release(Key.backspace)


def press_enter():

    if SYSTEM == "Windows":

        keyboard.send("enter")

    else:

        kb.press(Key.enter)
        kb.release(Key.enter)


def write_text(text):

    if SYSTEM == "Windows":

        keyboard.write(text)

    else:

        kb.type(text)


def type_code(lines):

    indent_stack = []
    line_count = 0

    for line in lines:

        if (
            not line.strip()
            or len(line.strip()) > MAX_LINE_LEN
        ):
            continue

        clean_line = line.strip()

        if clean_line.startswith("#IS"):

            indent_stack.append(
                clean_line
            )

            continue

        elif clean_line.startswith("#IE"):

            if indent_stack:

                indent_stack.pop()

                press_backspace()

                time.sleep(0.25)

            continue

        clean_line = line.lstrip()

        word_buffer = ""
        char_count = 0

        for ch in clean_line:

            char_count += 1

            if (
                random.random()
                < TYPO_PROBABILITY
                and ch.isalpha()
            ):

                wrong_char = random.choice(
                    "abcdefghijklmnopqrstuvwxyz"
                )

                write_text(
                    wrong_char
                )

                time.sleep(
                    random.uniform(
                        0.05,
                        0.2
                    )
                )

                press_backspace()

                time.sleep(
                    BACKSPACE_DELAY
                )

            write_text(ch)

            word_buffer += ch

            time.sleep(
                delay_for_char(ch)
            )

            if ch in (" ", "\t"):

                if word_buffer.strip():

                    time.sleep(
                        random.uniform(
                            *WORD_PAUSE_RANGE
                        )
                    )

                word_buffer = ""

            if char_count > MAX_LINE_LEN:

                break

        write_text(" ")

        time.sleep(0.001)

        press_enter()

        line_count += 1

        time.sleep(
            random.uniform(
                *LINE_DELAY_RANGE
            )
        )

        if (
            line_count
            % PAUSE_EVERY_N_LINES
            == 0
        ):

            time.sleep(
                PAUSE_DURATION
            )

    press_enter()


def type_text(text):

    lines = text.splitlines()

    type_code(lines)