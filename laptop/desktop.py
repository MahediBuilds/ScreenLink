"""Desktop automation: screenshots and clicks (Windows and macOS). Text entry is in typer.py."""

import io
import platform
import time

SYSTEM = platform.system()

if SYSTEM == "Windows":
    # Make screen sizes, screenshots and mouse positions all use physical pixels,
    # otherwise display scaling (125%, 150%...) makes clicks land in the wrong place.
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001 - older Windows versions
        ctypes.windll.user32.SetProcessDPIAware()

from PIL import ImageGrab  # noqa: E402
from pynput.mouse import Button, Controller as MouseController  # noqa: E402

_mouse = MouseController()


def screen_size():
    """Size of the primary screen in mouse coordinates."""
    if SYSTEM == "Windows":
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    if SYSTEM == "Darwin":
        import Quartz

        bounds = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
        return int(bounds.size.width), int(bounds.size.height)
    raise RuntimeError(f"Unsupported operating system: {SYSTEM}")


def screenshot_jpeg(quality):
    """Capture the primary screen and return (jpeg_bytes, width, height)."""
    image = ImageGrab.grab().convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue(), image.width, image.height


def click(x, y):
    _mouse.position = (x, y)
    time.sleep(0.1)  # let the target register the hover
    _mouse.position = (x, y)  # re-place in case the physical mouse moved meanwhile
    _mouse.click(Button.left)

