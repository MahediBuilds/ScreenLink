# ScreenLink

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Android 8.0+](https://img.shields.io/badge/Android-8.0%2B-3DDC84)
![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB)

**Control your laptop from your Android phone over your local Wi-Fi.** Capture the laptop's screen, send it to
any AI app on your phone with a ready-made prompt, then have the laptop type the answer or click where the AI
points.

ScreenLink never talks to an AI service itself. You choose the AI app and copy its answer back. There's no cloud
backend, no account and no internet requirement: the phone talks directly to the laptop on your network.

## Features

- **On-demand screenshots** of the laptop, with pinch-to-zoom, Android sharing and Save to gallery.
- **Prompt templates** stored as editable `.txt` files (Python, GUI, …), plus a Custom
  prompt you write in the app.
- **One-tap sharing** of the screenshot and prompt to ChatGPT, Gemini, Claude or any app that accepts images.
- **Type on laptop:** types the AI's answer line by line, with human-like timing, into whichever window is
  focused, with live progress and a Cancel button.
- **Click on laptop:** glides the mouse to each point from an AI reply to the GUI prompt, at a natural human
  speed along a slightly curved path, then clicks. Coordinates work at any screen resolution.
- **Pairing:** a one-time code shown on the laptop links the phone. Knowing the laptop's IP address isn't enough
  to control it.
- **Clear errors** that say whether the laptop is unreachable, the port is blocked, or the phone isn't paired.

## How it works

```
 ┌────────────────────────┐         local Wi-Fi / hotspot        ┌───────────────────────────┐
 │  Android app           │  ── HTTP: pair, screenshot, type, ──► │  Laptop client (Python)   │
 │  Kotlin, Compose       │        click, cancel                  │  Windows or macOS         │
 │  prompts, share sheet  │  ◄── JPEG screenshot, job status ──   │  screen, keyboard, mouse  │
 └────────────────────────┘                                       └───────────────────────────┘
        ▲      │ share screenshot + prompt
        │      ▼
   copy answer   AI app of your choice (ChatGPT, Gemini, Claude, …)
```

| Folder | What's in it |
|---|---|
| [`android/`](android/README.md) | The Android app (Kotlin, Jetpack Compose). Prompt files are in `app/src/main/assets/prompts/`. |
| [`laptop/`](laptop/README.md) | The Python laptop client: a small HTTP API, pairing, screenshots, typing and clicking. |
| [`tests/`](tests/) | Automated tests for the laptop API. The desktop is mocked, so nothing is really typed or clicked. |

## Quick start

### 1. Run the laptop client

You need Python 3.9 or later on Windows 10/11 or macOS.

```powershell
git clone https://github.com/MahediBuilds/ScreenLink.git
cd ScreenLink\laptop
python -m pip install -r requirements.txt
python client.py
```

The console shows the laptop's IP address, the port and a pairing code:

```
  ScreenLink laptop client
  Listening on port 5001
  Laptop IP:     192.168.1.20
  Paired phones: 0
  Pairing code:  482913
  Press Ctrl+C to stop.
```

Windows may ask whether Python can use the network. Allow it, or add a firewall rule for port 5001 (see the
[laptop guide](laptop/README.md#windows-firewall)).

### 2. Install the app

Download `ScreenLink-vX.Y.Z.apk` from [Releases](https://github.com/MahediBuilds/ScreenLink/releases) and open it
on your phone (Android 8.0 or later). You'll need to allow "install unknown apps". To build the APK yourself, see
the [Android guide](android/README.md).

### 3. Pair and use it

1. Connect the phone and laptop to the same Wi-Fi, or connect the laptop to the phone's hotspot.
2. In ScreenLink, enter the laptop IP and port, tap **Connect**, then enter the pairing code and tap **Pair**.
3. Tap **Take screenshot**. Pick a prompt tab, then tap **Share screenshot + prompt** and choose your AI app.
4. Copy the AI's answer, go back to ScreenLink and tap **Paste**.
5. On the laptop, click into the window that should receive the text. Then tap **Send text to laptop**, or, for a
   GUI-prompt answer, **Execute clicks on laptop**.

You only pair once. Both devices remember the pairing across restarts.

## Prompts

Each built-in prompt is a plain text file in
[`android/app/src/main/assets/prompts/`](android/app/src/main/assets/prompts). The file name becomes the tab name
(`_` and `-` show as spaces, so `My_prompt.txt` shows as "My prompt"). Tabs appear in this order: **General**, **Python**,
**GUI**, then the rest alphabetically, and finally **Custom**. To change, add or remove a prompt, edit the files
and rebuild the APK. The **Custom** tab is edited in the app and saved on the phone.

| Prompt | Expected answer | What to do with it |
|---|---|---|
| Python | Python code with `#IS`/`#IE` [indentation markers](laptop/README.md#indentation-markers) for auto-indenting editors | **Send text to laptop** |
| GUI | JSON with click points | **Execute clicks on laptop** |

## Troubleshooting

| The app shows | Likely cause |
|---|---|
| *No response from IP:port* | The client isn't running, the IP is wrong, Windows Firewall blocks the port, the devices are on different networks, or the Wi-Fi isolates clients (common on guest, public, university and hotel networks). |
| *Could not connect … ECONNREFUSED* | The laptop is reachable, but nothing is listening on that port. |
| *No route to host* | The phone and laptop are on different networks. |
| *Something answered … not the ScreenLink client* | Another program uses the port. Start the client with `--port`. |
| *Not paired* / *Wrong pairing code* | Enter the code currently shown in the laptop console. Codes are single use. |
| *Pairing is locked* | Too many wrong codes. Restart the laptop client. |

If the laptop client says *Cannot listen … Is another ScreenLink client already running?*, close the other window,
or use another port.

## Security

ScreenLink is designed for networks you trust, such as your home Wi-Fi or your own hotspot.

- Control requests need a 256-bit token, issued only for the one-time pairing code shown on the laptop. The
  laptop stores only hashes of tokens and never logs them, or the text you send.
- **Traffic is plain HTTP and isn't encrypted.** Someone else on the same network who can capture packets could
  see screenshots, typed text and the token. Don't use ScreenLink on untrusted networks. Never expose the port to
  the internet. If you think the token leaked, run `python client.py --reset-pairing`.
- The client only takes screenshots, types the text you send and clicks validated points. It never runs code or
  shell commands from an AI answer, and every action starts from a button you press.

To report a vulnerability, see [SECURITY.md](SECURITY.md).

## Contributing

Contributions are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) explains the setup, tests and pull-request
guidelines.

## License

[MIT](LICENSE) © 2026 MahediBuilds
