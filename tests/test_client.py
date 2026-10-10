"""Tests for the laptop client HTTP API and typer.

The real HTTP server runs on 127.0.0.1; the desktop (screen, mouse) is replaced by FakeDesktop and the
typer's keyboard by FakeKeyboard, so nothing is typed or clicked on this machine. Typing delays are set
to zero and typos are off unless a test turns them on.
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
import typer  # noqa: E402
from config import DEFAULTS  # noqa: E402
from pynput.keyboard import Key  # noqa: E402


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


class FakeKeyboard:
    """Stands in for pynput's keyboard Controller; records Backspace as "\\b" and Enter as "\\n"."""

    def __init__(self, desktop):
        self.desktop = desktop

    def type(self, ch):
        self.desktop.type_char(ch)

    def press(self, key):
        self.desktop.type_char({Key.backspace: "\b", Key.enter: "\n"}[key])

    def release(self, key):
        pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    config = dict(DEFAULTS, host="127.0.0.1", port=0, type_start_delay=0.0, click_interval=0.0)
    desktop = FakeDesktop()
    monkeypatch.setattr(typer, "kb", FakeKeyboard(desktop))
    monkeypatch.setattr(typer, "delay_for_char", lambda ch: 0.0)
    monkeypatch.setattr(typer, "WORD_PAUSE_RANGE", (0.0, 0.0))
    monkeypatch.setattr(typer, "LINE_DELAY_RANGE", (0.0, 0.0))
    monkeypatch.setattr(typer, "PAUSE_DURATION", 0.0)
    monkeypatch.setattr(typer, "BACKSPACE_DELAY", 0.0)
    monkeypatch.setattr(typer, "TYPO_PROBABILITY", 0.0)
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
    assert job["state"] == "done" and job["typed"] == job["total"] == 4
    # Each line ends with a space and Enter, plus a final Enter.
    assert "".join(desktop.typed) == "hi \nyo \n\n"


@pytest.mark.parametrize("body,expected", [
    ({}, 400), ({"text": ""}, 400), ({"text": "   "}, 400), ({"text": 5}, 400),
    ({"text": "#IS1\n\n#IE1"}, 400),                  # only markers: nothing to type
    ({"text": "a" * 301}, 400),                        # the only line is over MAX_LINE_LEN
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


# ----- typer: indentation markers (Python prompt) ---------------------------

def type_via_api(env, text):
    app, desktop, base = env
    token = pair(app, base)
    status, _ = jcall(base, "POST", "/type", {"text": text}, token=token)
    assert status == 202
    job = wait_for_job(base, token)
    assert job["state"] == "done"
    return "".join(desktop.typed), job


def test_markers_example_from_python_prompt(env):
    code = "if n>0:\n#IS1\nfact=1\nfor i in range(1,n+1):\n#IS2\nfact*=i\n#IE2\nprint(fact)\n#IE1"
    typed, job = type_via_api(env, code)
    assert typed == "if n>0: \nfact=1 \nfor i in range(1,n+1): \nfact*=i \n\bprint(fact) \n\b\n"
    assert job["typed"] == job["total"] == len("if n>0:fact=1for i in range(1,n+1):fact*=iprint(fact)")


def test_markers_strip_real_indentation_and_skip_blank_lines(env):
    code = "def f(x):\n    #IS1\n    if x:\n        #IS2\n        return 1\n        #IE2\n\n    return 0\n    #IE1\nprint(f(1))"
    typed, _ = type_via_api(env, code)
    assert typed == "def f(x): \nif x: \nreturn 1 \n\breturn 0 \n\bprint(f(1)) \n\n"


def test_unmatched_end_marker_is_ignored(env):
    typed, _ = type_via_api(env, "x=1\n#IE1\ny=2")
    assert typed == "x=1 \ny=2 \n\n"


# ----- typer: line handling ---------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("  42  \n", "42"),
    ("\n\nParis\n\n", "Paris"),
    # One content line between markers: typed without space/Enter; #IE still presses Backspace.
    ("#IS1\nprint(1)\n#IE1", "print(1)\b"),
])
def test_single_line_answer_is_stripped_without_enter(env, text, expected):
    typed, _ = type_via_api(env, text)
    assert typed == expected


def test_multi_line_text_is_left_stripped_and_blank_lines_skipped(env):
    typed, _ = type_via_api(env, "Hi Sam,\n\n  Thanks for the update.\n\nBest,\nAlex\n")
    assert typed == "Hi Sam, \nThanks for the update. \nBest, \nAlex \n\n"


def test_lines_longer_than_max_are_skipped(env):
    long_line = "a" * (typer.MAX_LINE_LEN + 1)
    typed, job = type_via_api(env, f"short\n{long_line}\nend")
    assert typed == "short \nend \n\n"
    assert job["total"] == len("shortend")


def test_typos_are_typed_and_corrected(env, monkeypatch):
    monkeypatch.setattr(typer, "TYPO_PROBABILITY", 1.0)
    typed, job = type_via_api(env, "ab")
    keys = list(typed)
    # For every letter: a wrong letter, Backspace, then the right letter.
    assert len(keys) == 6
    assert keys[1] == "\b" and keys[2] == "a" and keys[4] == "\b" and keys[5] == "b"
    assert keys[0].isalpha() and keys[3].isalpha()
    assert job["typed"] == job["total"] == 2  # progress counts answer characters only


def test_long_pause_every_n_lines(monkeypatch):
    monkeypatch.setattr(typer, "kb", FakeKeyboard(FakeDesktop()))
    monkeypatch.setattr(typer, "TYPO_PROBABILITY", 0.0)
    run = typer.Typer(threading.Event())
    pauses = []
    monkeypatch.setattr(run, "sleep", pauses.append)
    run.type_code([f"line{i}" for i in range(8)])
    assert pauses.count(typer.PAUSE_DURATION) == 8 // typer.PAUSE_EVERY_N_LINES


def test_delay_for_char_matches_wpm_range():
    for _ in range(500):
        letter = typer.delay_for_char("a")
        # 10-50 WPM (5 chars per word) -> 0.24-1.2 s per char, times 0.7-1.1 for letters.
        assert 60 / (50 * 5) * 0.7 <= letter <= 60 / (10 * 5) * 1.1
        assert typer.delay_for_char(".") >= 60 / (50 * 5) * 2.0


def test_cancel_during_a_pause_stops_typing(env, monkeypatch):
    monkeypatch.setattr(typer, "PAUSE_DURATION", 30.0)  # long pause after 4 lines
    app, desktop, base = env
    token = pair(app, base)
    jcall(base, "POST", "/type", {"text": "a\nb\nc\nd\ne\nf"}, token=token)
    time.sleep(0.3)  # now inside the 30 s pause
    started = time.time()
    jcall(base, "POST", "/type/cancel", {}, token=token)
    job = wait_for_job(base, token)
    assert job["state"] == "cancelled" and job["typed"] == 4
    assert time.time() - started < 2


def test_second_server_cannot_take_the_same_port(env):
    app, _, base = env
    port = int(base.rsplit(":", 1)[1])
    with pytest.raises(OSError):
        client.ScreenLinkServer(("127.0.0.1", port), app)
