"""ScreenLink laptop client.

A small HTTP API used by the ScreenLink Android app on the same Wi-Fi network:

  GET  /status         public    is this a ScreenLink client, is my token valid
  POST /pair           public    exchange the console pairing code for a token
  GET  /screenshot     token     JPEG of the primary screen
  POST /type           token     start typing text           -> 202 + job
  GET  /type           token     state of the current/last typing job
  POST /type/cancel    token     cancel the typing job
  POST /click          token     click normalized (0-1000) points

Run:  python client.py          Stop:  Ctrl+C
"""

import argparse
import hashlib
import hmac
import json
import math
import os
import secrets
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import PAIRED_FILE, load_config

API_VERSION = 1
_log_lock = threading.Lock()


def log(message):
    with _log_lock:
        print(time.strftime("[%H:%M:%S] ") + message, flush=True)


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def parse_click_steps(data, max_steps):
    """Validate a click request and return a list of normalized (x, y) points.

    Schema (matches the click prompt):
      {"steps": [{"action": "click", "point": {"x": 0-1000, "y": 0-1000},
                  "target": "optional label", "confidence": optional}]}
    The whole request is rejected if any step is invalid.
    """
    steps = data.get("steps") if isinstance(data, dict) else None
    if not isinstance(steps, list) or not steps:
        raise RequestError(400, "'steps' must be a non-empty list")
    if len(steps) > max_steps:
        raise RequestError(400, f"At most {max_steps} click steps are allowed")

    points = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise RequestError(400, f"Step {index} must be an object")
        if step.get("action") != "click":
            raise RequestError(400, f"Step {index}: only action 'click' is supported")
        point = step.get("point")
        if not isinstance(point, dict):
            raise RequestError(400, f"Step {index}: missing 'point' object")
        coords = []
        for axis in ("x", "y"):
            value = point.get(axis)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RequestError(400, f"Step {index}: point.{axis} must be a number")
            if not math.isfinite(value) or not 0 <= value <= 1000:
                raise RequestError(400, f"Step {index}: point.{axis} must be between 0 and 1000")
            coords.append(float(value))
        points.append(tuple(coords))
    return points


def to_pixels(nx, ny, width, height):
    x = min(max(round(nx / 1000 * width), 0), width - 1)
    y = min(max(round(ny / 1000 * height), 0), height - 1)
    return x, y


class ScreenLink:
    """All client state; HTTP handling is in Handler below."""

    def __init__(self, config, desktop, paired_file=PAIRED_FILE):
        self.config = config
        self.desktop = desktop
        self.paired_file = paired_file
        self.devices = self._load_devices()
        self.pairing_code = self._new_pairing_code()
        self.pairing_failures = 0
        self.pairing_lock = threading.Lock()

        # One desktop action (typing or clicking) at a time.
        self.action_lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.job = {"id": 0, "state": "idle", "typed": 0, "total": 0, "error": None}
        self.job_lock = threading.Lock()

    # ----- pairing / auth -------------------------------------------------

    def _new_pairing_code(self):
        digits = self.config["pairing_code_digits"]
        return "".join(secrets.choice("0123456789") for _ in range(digits))

    def _load_devices(self):
        if not os.path.exists(self.paired_file):
            return []
        with open(self.paired_file, "r", encoding="utf-8") as f:
            return json.load(f).get("devices", [])

    def _save_devices(self):
        tmp = self.paired_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"devices": self.devices}, f, indent=2)
        os.replace(tmp, self.paired_file)

    def is_authorized(self, auth_header):
        if not auth_header or not auth_header.startswith("Bearer "):
            return False
        candidate = token_hash(auth_header[len("Bearer "):].strip())
        # Check every device so timing does not reveal which one matched.
        matched = False
        for device in self.devices:
            if hmac.compare_digest(candidate, device["token_sha256"]):
                matched = True
        return matched

    def pairing_enabled(self):
        return self.pairing_failures < self.config["max_pairing_attempts"]

    def pair(self, code, device_name):
        with self.pairing_lock:
            if not self.pairing_enabled():
                raise RequestError(429, "Pairing is disabled after too many wrong codes. "
                                        "Restart the laptop client to get a new code.")
            if not isinstance(code, str) or not hmac.compare_digest(code.strip(), self.pairing_code):
                self.pairing_failures += 1
                left = self.config["max_pairing_attempts"] - self.pairing_failures
                log(f"Wrong pairing code ({left} attempts left)")
                if left <= 0:
                    log("Pairing disabled until restart")
                raise RequestError(403, "Wrong pairing code")

            token = secrets.token_urlsafe(32)
            name = (device_name if isinstance(device_name, str) else "")[:64] or "Android"
            self.devices.append({
                "name": name,
                "token_sha256": token_hash(token),
                "paired_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            self._save_devices()
            # Codes are single use; show the next one for pairing another phone.
            self.pairing_code = self._new_pairing_code()
            log(f"Paired with '{name}'. Next pairing code: {self.pairing_code}")
            return token

    # ----- screenshots ----------------------------------------------------

    def screenshot(self):
        try:
            return self.desktop.screenshot_jpeg(self.config["jpeg_quality"])
        except Exception as e:  # noqa: BLE001
            log(f"Screenshot failed: {e}")
            raise RequestError(500, f"Screenshot capture failed: {e}") from e

    # ----- text entry -----------------------------------------------------

    def job_snapshot(self):
        with self.job_lock:
            return dict(self.job)

    def _update_job(self, **changes):
        with self.job_lock:
            self.job.update(changes)

    def start_typing(self, text, strip_indent):
        if not isinstance(text, str) or not text.strip():
            raise RequestError(400, "'text' must be a non-empty string")
        if len(text) > self.config["max_text_chars"]:
            raise RequestError(413, f"Text is longer than {self.config['max_text_chars']} characters")
        if not isinstance(strip_indent, bool):
            raise RequestError(400, "'strip_indent' must be true or false")

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if strip_indent:
            # For editors that auto-indent new lines (IDEs, code boxes).
            text = "\n".join(line.lstrip(" \t") for line in text.split("\n"))

        if not self.action_lock.acquire(blocking=False):
            raise RequestError(409, "Another action is already running")
        self.cancel_event.clear()
        with self.job_lock:
            self.job = {"id": self.job["id"] + 1, "state": "typing",
                        "typed": 0, "total": len(text), "error": None}
            job = dict(self.job)
        log(f"Typing job {job['id']} started ({len(text)} characters)")
        threading.Thread(target=self._type_worker, args=(text,), daemon=True).start()
        return job

    def _type_worker(self, text):
        state, error = "done", None
        try:
            if self.cancel_event.wait(self.config["type_start_delay"]):
                state = "cancelled"
                return
            for count, ch in enumerate(text, start=1):
                if self.cancel_event.is_set():
                    state = "cancelled"
                    return
                self.desktop.type_char(ch)
                self._update_job(typed=count)
                if self.cancel_event.wait(self.config["type_char_interval"]):
                    state = "cancelled" if count < len(text) else "done"
                    return
        except Exception as e:  # noqa: BLE001
            state, error = "error", f"Typing failed: {e}"
        finally:
            self._update_job(state=state, error=error)
            log(f"Typing job {self.job['id']} finished: {state}" + (f" ({error})" if error else ""))
            self.action_lock.release()

    def cancel_typing(self):
        running = self.job_snapshot()["state"] == "typing"
        if running:
            self.cancel_event.set()
            log("Typing cancel requested")
        return running

    # ----- clicks ---------------------------------------------------------

    def click(self, data):
        points = parse_click_steps(data, self.config["max_click_steps"])
        if not self.action_lock.acquire(blocking=False):
            raise RequestError(409, "Another action is already running")
        try:
            width, height = self.desktop.screen_size()
            pixels = [to_pixels(x, y, width, height) for x, y in points]
            for index, (x, y) in enumerate(pixels):
                if index:
                    time.sleep(self.config["click_interval"])
                self.desktop.click(x, y)
            log(f"Clicked {len(pixels)} point(s) on {width}x{height} screen")
            return {"clicked": len(pixels), "screen": [width, height],
                    "pixels": [list(p) for p in pixels]}
        except Exception as e:  # noqa: BLE001
            log(f"Click failed: {e}")
            raise RequestError(500, f"Click failed: {e}") from e
        finally:
            self.action_lock.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "ScreenLink"
    timeout = 20  # seconds; drops stalled connections

    @property
    def app(self):
        return self.server.app

    def log_message(self, format, *args):  # noqa: A002 - keep default access log quiet
        pass

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise RequestError(415, "Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise RequestError(411, "Content-Length required") from None
        if length < 0 or length > self.app.config["max_body_bytes"]:
            raise RequestError(413, "Request body too large")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise RequestError(400, "Body must be valid JSON") from None
        if not isinstance(data, dict):
            raise RequestError(400, "Body must be a JSON object")
        return data

    def require_auth(self):
        if not self.app.is_authorized(self.headers.get("Authorization")):
            raise RequestError(401, "Not paired or invalid token. Pair the app again.")

    def handle_route(self, method):
        path = self.path.split("?")[0]
        app = self.app

        if method == "GET" and path == "/status":
            return self.send_json(200, {
                "ok": True, "app": "ScreenLink", "api": API_VERSION,
                "hostname": socket.gethostname(),
                "authorized": app.is_authorized(self.headers.get("Authorization")),
                "pairing_enabled": app.pairing_enabled(),
            })

        if method == "POST" and path == "/pair":
            data = self.read_json()
            token = app.pair(data.get("code"), data.get("device"))
            return self.send_json(200, {"ok": True, "token": token, "hostname": socket.gethostname()})

        routes = {
            ("GET", "/screenshot"), ("GET", "/type"), ("POST", "/type"),
            ("POST", "/type/cancel"), ("POST", "/click"),
        }
        if (method, path) not in routes:
            raise RequestError(404, "Unknown endpoint")
        self.require_auth()

        if path == "/screenshot":
            jpeg, width, height = app.screenshot()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.send_header("X-Screen-Width", str(width))
            self.send_header("X-Screen-Height", str(height))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(jpeg)
            log(f"Screenshot sent ({width}x{height}, {len(jpeg) // 1024} KB)")
        elif method == "GET" and path == "/type":
            self.send_json(200, {"ok": True, "job": app.job_snapshot()})
        elif path == "/type":
            data = self.read_json()
            job = app.start_typing(data.get("text"), data.get("strip_indent", False))
            self.send_json(202, {"ok": True, "job": job})
        elif path == "/type/cancel":
            self.read_json()
            cancelled = app.cancel_typing()
            self.send_json(200, {"ok": True, "cancel_requested": cancelled, "job": app.job_snapshot()})
        elif path == "/click":
            result = app.click(self.read_json())
            self.send_json(200, {"ok": True, **result})

    def dispatch(self, method):
        try:
            self.handle_route(method)
        except RequestError as e:
            self.send_json(e.status, {"ok": False, "error": e.message})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass  # phone went away mid-request
        except Exception as e:  # noqa: BLE001 - never let a request crash the client
            log(f"Unexpected error: {e!r}")
            try:
                self.send_json(500, {"ok": False, "error": "Internal error"})
            except OSError:
                pass

    def do_GET(self):  # noqa: N802
        self.dispatch("GET")

    def do_POST(self):  # noqa: N802
        self.dispatch("POST")


class ScreenLinkServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app):
        super().__init__(address, Handler)
        self.app = app


def local_ips():
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is sent; picks the default route
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def main():
    parser = argparse.ArgumentParser(description="ScreenLink laptop client")
    parser.add_argument("--host", help="interface to listen on (default from config)")
    parser.add_argument("--port", type=int, help="port to listen on (default from config)")
    parser.add_argument("--reset-pairing", action="store_true",
                        help="forget all paired phones before starting")
    args = parser.parse_args()

    config = load_config()
    if args.host:
        config["host"] = args.host
    if args.port:
        config["port"] = args.port
    if args.reset_pairing and os.path.exists(PAIRED_FILE):
        os.remove(PAIRED_FILE)
        log("Forgot all paired phones")

    import desktop  # imported here so tests never touch the real desktop

    app = ScreenLink(config, desktop)
    try:
        server = ScreenLinkServer((config["host"], config["port"]), app)
    except OSError as e:
        log(f"Cannot listen on {config['host']}:{config['port']}: {e}")
        sys.exit(1)

    print()
    print("  ScreenLink laptop client")
    print(f"  Listening on port {config['port']}")
    for ip in local_ips() or ["(no network address found)"]:
        print(f"  Laptop IP:     {ip}")
    print(f"  Paired phones: {len(app.devices)}")
    print(f"  Pairing code:  {app.pairing_code}")
    print("  Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        log("Stopping...")
        app.cancel_event.set()
        server.server_close()
        log("Stopped")


if __name__ == "__main__":
    main()
