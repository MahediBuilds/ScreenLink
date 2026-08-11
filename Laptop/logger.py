import os
import time
import traceback


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

LOG_DIR = os.path.join(
    BASE_DIR,
    "logs"
)

os.makedirs(
    LOG_DIR,
    exist_ok=True
)

START_TIME = time.strftime(
    "%Y%m%d_%H%M%S"
) + f"_{int(time.time() * 1000) % 1000:03d}"

LOG_FILE = os.path.join(
    LOG_DIR,
    f"{START_TIME}.log"
)


def log(message):

    timestamp = time.strftime(
        "[%Y-%m-%d %H:%M:%S]"
    )

    line = f"{timestamp} {message}"

    print(line)

    try:

        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(line + "\n")

    except Exception:
        pass


def log_error(message):

    log(
        "ERROR: " + message
    )

    try:

        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                traceback.format_exc()
                + "\n"
            )

    except Exception:
        pass


def get_log_file():

    return LOG_FILE