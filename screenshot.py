import os
import platform
import subprocess
import time

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

    system = platform.system()

    log(
        f"Operating system -> {system}"
    )

    try:

        if system == "Windows":

            capture_windows(path)

        elif system == "Darwin":

            capture_macos(path)

        else:

            log_error(
                f"Unsupported operating system -> "
                f"{system}"
            )

            return None

        if not os.path.exists(path):

            log_error(
                "Screenshot file was not created"
            )

            return None

        size = os.path.getsize(path)

        if size == 0:

            log_error(
                "Screenshot file is empty"
            )

            return None

        log(
            f"Screenshot saved -> {path}"
        )

        log(
            f"Screenshot size -> {size} bytes"
        )

        return {
            "path": path,
            "timestamp": timestamp,
            "filename": filename,
            "size": size
        }

    except Exception as e:

        log_error(
            "Screenshot failed: "
            + str(e)
        )

        return None


def capture_windows(path):

    log(
        "Using Windows screenshot method"
    )

    try:

        import mss

        with mss.mss() as sct:

            sct.shot(
                output=path
            )

    except Exception as e:

        log_error(
            "Windows screenshot failed: "
            + str(e)
        )

        raise


def capture_macos(path):

    log(
        "Using macOS screenshot method"
    )

    result = subprocess.run(
        [
            "screencapture",
            "-x",
            path
        ],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:

        raise RuntimeError(
            "macOS screencapture failed: "
            + result.stderr
        )