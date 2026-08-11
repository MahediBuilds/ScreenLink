import os
import time
import mss

from logger import log, log_error


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SCREENSHOT_DIR = os.path.join(
    BASE_DIR,
    "screenshots"
)

os.makedirs(
    SCREENSHOT_DIR,
    exist_ok=True
)


def capture_screen():

    timestamp = time.strftime(
        "%Y%m%d_%H%M%S"
    ) + f"_{int(time.time() * 1000) % 1000:03d}"

    filename = (
        f"{timestamp}.png"
    )

    path = os.path.join(
        SCREENSHOT_DIR,
        filename
    )

    try:

        log(
            "Capturing screenshot..."
        )

        with mss.mss() as sct:

            sct.shot(
                output=path
            )

        size = os.path.getsize(
            path
        )

        log(
            f"Screenshot saved -> {path}"
        )

        log(
            f"Screenshot size -> "
            f"{size} bytes"
        )

        return {
            "path": path,
            "timestamp": timestamp,
            "filename": filename
        }

    except Exception as e:

        log_error(
            "Screenshot failed: "
            + str(e)
        )

        return None