# ScreenLink laptop client

A small Python program that lets the ScreenLink Android app take screenshots of this computer, type text and
click points. It runs an HTTP API on your local network. Nothing is sent to the internet.

| File | Purpose |
|---|---|
| `client.py` | HTTP API, pairing and authentication, request validation, the typing job, command-line entry point |
| `typer.py` | Text entry: types the answer line by line with human-like timing (see [Typing](#typing)) |
| `desktop.py` | Screen capture and mouse clicks with human-like pointer movement (Windows and macOS) |
| `config.py` | All settings and their defaults |
| `requirements.txt` | Dependencies: Pillow and pynput |

## Requirements

- Windows 10/11 (the primary target) or macOS
- Python 3.9 or later

## Install and run

```powershell
cd laptop
python -m pip install -r requirements.txt
python client.py
```

The console prints the laptop's IP address, the port and a 6-digit pairing code. Enter the IP and port in the
app, then the code. Press **Ctrl+C** to stop. Stopping also cancels any typing in progress.

| Option | Effect |
|---|---|
| `--port 5050` | Listen on a different port (default 5001) |
| `--host 192.168.1.20` | Listen on one interface only (default: all interfaces) |
| `--reset-pairing` | Forget every paired phone before starting |

Only one client can use a port at a time. A second client on the same port exits with *Is another ScreenLink
client already running?*.

### macOS permissions

Give your terminal app **Screen Recording** and **Accessibility** permission (System Settings → Privacy &
Security). Without them, screenshots come out blank and typing or clicking does nothing.

### Finding the laptop's IP address

The client prints it at startup. You can also run `ipconfig` (Windows) or `ipconfig getifaddr en0` (macOS) and
use the IPv4 address of the Wi-Fi adapter. It's usually `192.168.x.x`, `10.x.x.x` or `172.16–31.x.x`. Ignore VPN
and virtual adapters (WSL, Hyper-V, VirtualBox).

### Windows Firewall

The first time Python listens on the network, Windows may ask whether to allow it. A rule limited to
ScreenLink's port is tighter than allowing Python on every port. Run this in an **administrator** PowerShell:

```powershell
New-NetFirewallRule -DisplayName "ScreenLink" -Direction Inbound -Protocol TCP -LocalPort 5001 -Action Allow -Profile Private,Public
```

Remove the rule with `Remove-NetFirewallRule -DisplayName "ScreenLink"`. Only allow it on networks you trust.

## Configuration

Defaults live in `config.py`. To override any of them, create `laptop/config.json` containing only the keys you
want to change, for example `{"port": 5050, "max_click_steps": 5}`. This file is git-ignored, and unknown keys are
rejected.

| Key | Default | Meaning |
|---|---|---|
| `host` | `0.0.0.0` | Interface to listen on |
| `port` | `5001` | TCP port |
| `max_body_bytes` | `65536` | Largest accepted request body |
| `pairing_code_digits` | `6` | Length of the pairing code |
| `max_pairing_attempts` | `5` | Wrong codes allowed before pairing locks until restart |
| `jpeg_quality` | `80` | Screenshot JPEG quality |
| `max_text_chars` | `20000` | Longest text accepted for typing |
| `type_start_delay` | `1.0` | Seconds before typing starts |
| `max_click_steps` | `10` | Most clicks allowed per request |
| `click_interval` | `0.25` | Seconds between clicks |

Paired phones are stored in `laptop/paired.json` as SHA-256 hashes of their tokens. This file is git-ignored.

## Typing

`typer.py` types the answer line by line with human-like timing. Its settings are constants at the top of the
file:

| Constant | Default | Meaning |
|---|---|---|
| `MIN_WPM`, `MAX_WPM` | `10`, `50` | Typing speed range, picked at random for every character |
| `TYPO_PROBABILITY` | `0.015` | Chance per letter of typing a wrong letter first, then deleting it |
| `WORD_PAUSE_RANGE` | `0.5`–`1.2` s | Pause after each word |
| `LINE_DELAY_RANGE` | `0.3`–`0.9` s | Pause after each line |
| `PAUSE_EVERY_N_LINES`, `PAUSE_DURATION` | `4`, `5` s | A longer pause after every 4 lines |
| `MAX_LINE_LEN` | `300` | Lines longer than this are skipped |

Punctuation, brackets and spaces get extra delay. At these settings typing is slow, about 1–2 characters per
second plus pauses, so long answers take minutes. The app shows progress (typos aren't counted), and **Cancel
typing** stops it at the next keystroke or pause.

Line handling:

- Blank lines are skipped, and each line is typed without its leading indentation.
- Each line ends with a space, then Enter, which keeps Enter from accepting an editor's autocomplete
  suggestion. One more Enter follows the last line.
- **One-line answers:** if exactly one line would be typed (ignoring markers and over-long lines), it's typed
  trimmed, with no trailing space or Enter, so it doesn't submit a form or add a new line.

### Indentation markers

Many code editors indent automatically after a line that ends with `:`. The bundled Python prompt asks the AI to
mark blocks so that indentation comes out right:

```
if n>0:
#IS1
fact=1
#IE1
```

Lines starting with `#IS` are skipped. Each line starting with `#IE` presses **Backspace** once, to step out of the
block the editor indented. An `#IE` without a matching `#IS` is ignored.

## HTTP API

Version 1. All bodies are JSON (`Content-Type: application/json`). Endpoints marked *token* need
`Authorization: Bearer <token>`. Errors return `{"ok": false, "error": "..."}` with a fitting status code (400,
401, 403, 404, 409, 413, 415, 429 or 500).

| Method | Path | Auth | Request → Response |
|---|---|---|---|
| GET | `/status` | none | → `{"app": "ScreenLink", "api": 1, "hostname", "authorized", "pairing_enabled"}` |
| POST | `/pair` | code | `{"code": "123456", "device": "Pixel 8"}` → `{"token": "..."}` |
| GET | `/screenshot` | token | → `image/jpeg` of the primary screen, with `X-Screen-Width` and `X-Screen-Height` headers |
| POST | `/type` | token | `{"text": "..."}` → `202 {"job": {...}}` (`total` = answer characters to type) |
| GET | `/type` | token | → `{"job": {"id", "state", "typed", "total", "error"}}`, where `state` is `typing`, `done`, `cancelled`, `error` or `idle` |
| POST | `/type/cancel` | token | `{}` → `{"cancel_requested": true/false, "job": {...}}` |
| POST | `/click` | token | see below → `{"clicked": n, "screen": [w, h], "pixels": [[x, y], ...]}` |

Only one desktop action (typing or clicking) runs at a time. A second request gets `409`.

Click requests use the format the GUI prompt asks the AI to return. Coordinates are normalized from 0 to 1000
across the primary screen:

```json
{"steps": [{"action": "click", "target": "Submit button", "confidence": 0.97, "point": {"x": 366, "y": 347}}]}
```

`action` must be `"click"`, and `x` and `y` must be numbers from 0 to 1000. `target` and `confidence` are
optional and ignored. If any step is invalid, the whole request is rejected before anything is clicked.

## Tests

From the repository root:

```powershell
python -m pip install pytest
python -m pytest tests
```

The tests start the real HTTP server on `127.0.0.1` with a fake desktop and keyboard, so nothing is typed or clicked on your
machine.
