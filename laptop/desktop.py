"""Desktop automation: screenshots and clicks (Windows and macOS). Text entry is in typer.py.

Clicks glide the pointer to the target like a hand would: a slightly curved path, a smooth speed-up and
slow-down, a duration that grows with distance, and sometimes a small overshoot that is then corrected.
"""

import io
import math
import platform
import random
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

# --- Mouse movement tuning ---
MOVE_BASE_SECONDS = 0.2        # duration = base + per_doubling * log2(1 + distance / 10), roughly Fitts's law
MOVE_PER_DOUBLING = 0.09       # so ~0.45 s for 50 px, ~0.7 s for 500 px, ~0.9 s across a 1920 px screen
MOVE_SPEED_JITTER = 0.15       # each move is up to 15% faster or slower
MOVE_STEP_SECONDS = 0.008      # pointer updates about 125 times a second
CURVE_RANGE = (0.03, 0.12)     # sideways bow of the path, as a fraction of the distance
OVERSHOOT_MIN_DISTANCE = 250   # only longer moves may overshoot
OVERSHOOT_PROBABILITY = 0.35
OVERSHOOT_RANGE = (4, 14)      # pixels past the target before correcting
HOVER_RANGE = (0.08, 0.2)      # pause on the target before pressing
CLICK_HOLD_RANGE = (0.05, 0.11)  # how long the button stays down


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


def _ease(t):
    """Minimum-jerk profile: starts slowly, is fastest mid-way and settles gently, like a real hand."""
    return t * t * t * (10 - 15 * t + 6 * t * t)


def move_path(start, end, rng=random):
    """Timed points [(seconds_from_start, x, y), ...] for a human-like move from start to end."""
    (x0, y0), (x1, y1) = start, end
    dx, dy = x1 - x0, y1 - y0
    distance = math.hypot(dx, dy)
    if distance < 1:
        return [(0.0, x1, y1)]
    duration = (MOVE_BASE_SECONDS + MOVE_PER_DOUBLING * math.log2(1 + distance / 10))         * rng.uniform(1 - MOVE_SPEED_JITTER, 1 + MOVE_SPEED_JITTER)

    # Cubic Bezier whose control points sit to one side of the straight line, so the path bows a little.
    nx, ny = -dy / distance, dx / distance
    side = rng.choice((-1, 1))
    bow1 = side * distance * rng.uniform(*CURVE_RANGE)
    bow2 = side * distance * rng.uniform(*CURVE_RANGE) * rng.uniform(0.3, 1.0)
    c1 = (x0 + dx * rng.uniform(0.2, 0.4) + nx * bow1, y0 + dy * rng.uniform(0.2, 0.4) + ny * bow1)
    c2 = (x0 + dx * rng.uniform(0.6, 0.8) + nx * bow2, y0 + dy * rng.uniform(0.6, 0.8) + ny * bow2)

    steps = max(2, int(duration / MOVE_STEP_SECONDS))
    points = []
    for i in range(1, steps + 1):
        u = _ease(i / steps)
        a, b, c, d = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u * u, u ** 3
        points.append((duration * i / steps,
                       a * x0 + b * c1[0] + c * c2[0] + d * x1,
                       a * y0 + b * c1[1] + c * c2[1] + d * y1))
    return points


def _play(points):
    """Moves the pointer along timed points, keeping to the schedule even if sleeps run long."""
    begin = time.perf_counter()
    for at, x, y in points:
        wait = at - (time.perf_counter() - begin)
        if wait > 0:
            time.sleep(wait)
        _mouse.position = (round(x), round(y))


def move_to(x, y, rng=random):
    """Glides the pointer to (x, y), sometimes overshooting slightly and correcting."""
    start = _mouse.position
    distance = math.hypot(x - start[0], y - start[1])
    if distance >= OVERSHOOT_MIN_DISTANCE and rng.random() < OVERSHOOT_PROBABILITY:
        past = rng.uniform(*OVERSHOOT_RANGE)
        aim = (x + (x - start[0]) / distance * past + rng.uniform(-3, 3),
               y + (y - start[1]) / distance * past + rng.uniform(-3, 3))
        _play(move_path(start, aim, rng))
        time.sleep(rng.uniform(0.03, 0.08))
        start = _mouse.position
    _play(move_path(start, (x, y), rng))


def click(x, y):
    move_to(x, y)
    time.sleep(random.uniform(*HOVER_RANGE))  # let the target register the hover
    _mouse.position = (x, y)  # re-place in case the physical mouse moved meanwhile
    _mouse.press(Button.left)
    time.sleep(random.uniform(*CLICK_HOLD_RANGE))
    _mouse.release(Button.left)

