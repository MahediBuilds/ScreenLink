"""Tests for the laptop client HTTP API.

The real HTTP server runs on 127.0.0.1; the desktop (screen, mouse, keyboard)
is replaced by FakeDesktop, so nothing is typed or clicked on this machine.
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "laptop"))

import client  # noqa: E402
from config import DEFAULTS  # noqa: E402


class FakeDesktop:
    def __init__(self):
        self.typed = []
        self.clicks = []
        self.fail_screenshot = False
        self.fail_typing_at = None
        self.char_delay = 0.0

    def screen_size(self):
        return 1920, 1080

    def screenshot_jpeg(self, quality):
        if self.fail_screenshot:
            raise OSError("no display")
        return b"\xff\xd8\xff\xe0fakejpeg\xff\xd9", 1920, 1080

    def click(self, x, y):
        self.clicks.append((x, y))

    def type_char(self, ch):
        if self.fail_typing_at is not None and len(self.typed) == self.fail_typing_at:
            raise OSError("keyboard unavailable")
        time.sleep(self.char_delay)
        self.typed.append(ch)


@pytest.fixture
def env(tmp_path):
    config = dict(DEFAULTS, host="127.0.0.1", port=0,
                  type_start_delay=0.0, type_char_interval=0.0, click_interval=0.0)
    desktop = FakeDesktop()
    app = client.ScreenLink(config, desktop, paired_file=str(tmp_path / "paired.json"))
    server = client.ScreenLinkServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    yield app, desktop, base
    server.shutdown()
    server.server_close()


def call(base, method, path, body=None, token=None, raw=None, content_type="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def jcall(*args, **kwargs):
    status, _, body = call(*args, **kwargs)
    return status, json.loads(body)


def pair(app, base):
    status, data = jcall(base, "POST", "/pair", {"code": app.pairing_code, "device": "Test phone"})
    assert status == 200
    return data["token"]


def wait_for_job(base, token, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, data = jcall(base, "GET", "/type", token=token)
        if data["job"]["state"] != "typing":
            return data["job"]
        time.sleep(0.02)
    raise AssertionError("typing job did not finish")


# ----- status & pairing ---------------------------------------------------

def test_status_is_public(env):
    app, _, base = env
    status, data = jcall(base, "GET", "/status")
    assert status == 200
    assert data["app"] == "ScreenLink" and data["authorized"] is False


def test_pairing_issues_token_and_persists_only_hash(env, tmp_path):
    app, _, base = env
    old_code = app.pairing_code
    token = pair(app, base)
    _, data = jcall(base, "GET", "/status", token=token)
    assert data["authorized"] is True
    assert app.pairing_code != old_code  # single use
    saved = (tmp_path / "paired.json").read_text()
    assert token not in saved and client.token_hash(token) in saved


def test_paired_token_survives_restart(env, tmp_path):
    app, desktop, base = env
    token = pair(app, base)
    restarted = client.ScreenLink(app.config, desktop, paired_file=str(tmp_path / "paired.json"))
    assert restarted.is_authorized(f"Bearer {token}")


def test_wrong_code_rejected_and_pairing_locks(env):
    app, _, base = env
    wrong = "x" * len(app.pairing_code)
    for _ in range(DEFAULTS["max_pairing_attempts"]):
        status, _ = jcall(base, "POST", "/pair", {"code": wrong})
        assert status == 403
    # Even the right code is refused once locked.
    status, data = jcall(base, "POST", "/pair", {"code": app.pairing_code})
    assert status == 429 and "Restart" in data["error"]


@pytest.mark.parametrize("method,path", [
    ("GET", "/screenshot"), ("GET", "/type"), ("POST", "/type"),
    ("POST", "/type/cancel"), ("POST", "/click"),
])
def test_control_endpoints_require_token(env, method, path):
    _, desktop, base = env
    body = {} if method == "POST" else None
    assert jcall(base, method, path, body)[0] == 401
    assert jcall(base, method, path, body, token="not-a-real-token")[0] == 401
    assert desktop.typed == [] and desktop.clicks == []


def test_unknown_endpoint(env):
    _, _, base = env
    assert jcall(base, "GET", "/nope")[0] == 404


# ----- request validation -------------------------------------------------

def test_rejects_wrong_content_type(env):
    app, _, base = env
    token = pair(app, base)
    status, _ = jcall(base, "POST", "/type", raw=b"text=hi", token=token, content_type="text/plain")
    assert status == 415


def test_rejects_invalid_json(env):
    app, _, base = env
    token = pair(app, base)
    assert jcall(base, "POST", "/type", raw=b"{not json", token=token)[0] == 400
    assert jcall(base, "POST", "/type", raw=b"[1,2]", token=token)[0] == 400


def test_rejects_oversized_body(env):
    app, _, base = env
    token = pair(app, base)
    big = json.dumps({"text": "a" * (DEFAULTS["max_body_bytes"] + 10)}).encode()
    assert jcall(base, "POST", "/type", raw=big, token=token)[0] == 413


# ----- screenshots --------------------------------------------------------

def test_screenshot_returns_jpeg(env):
    app, _, base = env
    token = pair(app, base)
    status, headers, body = call(base, "GET", "/screenshot", token=token)
    assert status == 200
    assert headers["Content-Type"] == "image/jpeg"
    assert headers["X-Screen-Width"] == "1920" and body.startswith(b"\xff\xd8")


def test_screenshot_failure_reported(env):
    app, desktop, base = env
    token = pair(app, base)
    desktop.fail_screenshot = True
    status, data = jcall(base, "GET", "/screenshot", token=token)
    assert status == 500 and "no display" in data["error"]


# ----- typing -------------------------------------------------------------

def test_typing_completes(env):
    app, desktop, base = env
    token = pair(app, base)
    status, data = jcall(base, "POST", "/type", {"text": "hi\r\nyo"}, token=token)
    assert status == 202 and data["job"]["state"] == "typing"
    job = wait_for_job(base, token)
    assert job["state"] == "done" and job["typed"] == job["total"] == 5
    assert "".join(desktop.typed) == "hi\nyo"


def test_typing_strip_indent(env):
    app, desktop, base = env
    token = pair(app, base)
    jcall(base, "POST", "/type", {"text": "def f():\n    return 1", "strip_indent": True}, token=token)
    wait_for_job(base, token)
    assert "".join(desktop.typed) == "def f():\nreturn 1"


@pytest.mark.parametrize("body,expected", [
    ({}, 400), ({"text": ""}, 400), ({"text": "   "}, 400), ({"text": 5}, 400),
    ({"text": "hi", "strip_indent": "yes"}, 400),
    ({"text": "a" * (DEFAULTS["max_text_chars"] + 1)}, 413),
])
def test_typing_validation(env, body, expected):
    app, desktop, base = env
    token = pair(app, base)
    assert jcall(base, "POST", "/type", body, token=token)[0] == expected
    assert desktop.typed == []


def test_typing_cancel(env):
    app, desktop, base = env
    token = pair(app, base)
    desktop.char_delay = 0.02
    jcall(base, "POST", "/type", {"text": "x" * 200}, token=token)
    time.sleep(0.1)
    status, data = jcall(base, "POST", "/type/cancel", {}, token=token)
    assert status == 200 and data["cancel_requested"] is True
    job = wait_for_job(base, token)
    assert job["state"] == "cancelled"
    assert 0 < job["typed"] < 200 and len(desktop.typed) == job["typed"]


def test_cancel_when_idle(env):
    app, _, base = env
    token = pair(app, base)
    _, data = jcall(base, "POST", "/type/cancel", {}, token=token)
    assert data["cancel_requested"] is False


def test_no_overlapping_actions(env):
    app, desktop, base = env
    token = pair(app, base)
    desktop.char_delay = 0.02
    jcall(base, "POST", "/type", {"text": "x" * 100}, token=token)
    assert jcall(base, "POST", "/type", {"text": "again"}, token=token)[0] == 409
    click = {"steps": [{"action": "click", "point": {"x": 1, "y": 1}}]}
    assert jcall(base, "POST", "/click", click, token=token)[0] == 409
    jcall(base, "POST", "/type/cancel", {}, token=token)
    wait_for_job(base, token)
    assert jcall(base, "POST", "/click", click, token=token)[0] == 200


def test_typing_error_reported_and_client_recovers(env):
    app, desktop, base = env
    token = pair(app, base)
    desktop.fail_typing_at = 2
    jcall(base, "POST", "/type", {"text": "hello"}, token=token)
    job = wait_for_job(base, token)
    assert job["state"] == "error" and "keyboard unavailable" in job["error"]
    desktop.fail_typing_at = None
    assert jcall(base, "POST", "/type", {"text": "ok"}, token=token)[0] == 202
    assert wait_for_job(base, token)["state"] == "done"


# ----- clicks -------------------------------------------------------------

def test_click_converts_normalized_points(env):
    app, desktop, base = env
    token = pair(app, base)
    body = {"steps": [
        {"action": "click", "target": "Java", "confidence": 0.99, "point": {"x": 500, "y": 500}},
        {"action": "click", "point": {"x": 0, "y": 1000}},
    ]}
    status, data = jcall(base, "POST", "/click", body, token=token)
    assert status == 200 and data["clicked"] == 2
    assert desktop.clicks == [(960, 540), (0, 1079)]


@pytest.mark.parametrize("body", [
    {},
    {"steps": []},
    {"steps": "click"},
    {"steps": [{"action": "double_click", "point": {"x": 1, "y": 1}}]},
    {"steps": [{"action": "click"}]},
    {"steps": [{"action": "click", "point": {"x": 1}}]},
    {"steps": [{"action": "click", "point": {"x": "1", "y": 1}}]},
    {"steps": [{"action": "click", "point": {"x": True, "y": 1}}]},
    {"steps": [{"action": "click", "point": {"x": 1001, "y": 1}}]},
    {"steps": [{"action": "click", "point": {"x": -1, "y": 1}}]},
    {"steps": [{"action": "click", "point": {"x": 1, "y": 1}}, "bad"]},
    {"steps": [{"action": "click", "point": {"x": 1, "y": 1}}] * (DEFAULTS["max_click_steps"] + 1)},
])
def test_click_rejects_malformed(env, body):
    app, desktop, base = env
    token = pair(app, base)
    assert jcall(base, "POST", "/click", body, token=token)[0] == 400
    assert desktop.clicks == []  # nothing executed, not even valid leading steps


def test_click_rejects_nan(env):
    app, desktop, base = env
    token = pair(app, base)
    raw = b'{"steps":[{"action":"click","point":{"x":NaN,"y":1}}]}'
    assert jcall(base, "POST", "/click", raw=raw, token=token)[0] == 400
    assert desktop.clicks == []
