# ScreenLink

Control your laptop from your Android phone over the local Wi-Fi network:

1. Take a screenshot of the laptop and view it on the phone.
2. Pick a prompt template, then copy or share the prompt and screenshot to an AI app of your choice.
3. Paste the AI's answer back into ScreenLink.
4. Choose to **type it on the laptop** or **click** the points it describes.

You handle the AI conversation yourself. ScreenLink never calls an AI service and has no cloud backend, no
accounts, and needs no internet connection.

## Architecture

```
 Android app (Kotlin, Jetpack Compose)  ── HTTP over Wi-Fi ──►  Laptop client (Python)
   connection, screenshots, prompts,                             screenshots, typing, clicks
   clipboard, share sheet, actions                                laptop/client.py, desktop.py
```

* **`android/`**: a native Android app. Prompt templates are bundled in `app/src/main/res/raw/`.
* **`laptop/`**: the Python client. `client.py` runs the HTTP API, pairing and validation. `desktop.py` does the
  screenshots, clicks and typing. `config.py` holds every setting.
* **`tests/`**: automated tests for the laptop API. The desktop is mocked, so nothing gets typed or clicked.

The phone connects directly to the laptop's private IP address, so both devices must be on the same network. A
phone hotspot that the laptop joins also works.

### Laptop API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/status` | none | Identifies the client and reports whether the sent token is valid |
| POST | `/pair` | pairing code | `{"code": "123456", "device": "Phone"}` returns `{"token": ...}` |
| GET | `/screenshot` | token | Returns the primary screen as `image/jpeg`, with `X-Screen-Width`/`-Height` headers |
| POST | `/type` | token | `{"text": "...", "strip_indent": false}` returns `202` and a job |
| GET | `/type` | token | Current or last typing job: `typing`, `done`, `cancelled` or `error`, with progress |
| POST | `/type/cancel` | token | Cancels the running typing job |
| POST | `/click` | token | Clicks the given points (schema below) and reports how many were clicked |

The token goes in an `Authorization: Bearer <token>` header. Only one desktop action (typing or clicking) runs at a
time, and a second request gets `409`.

Click requests use the format the **Click** prompt asks the AI to return. Coordinates are normalized from 0 to 1000,
so they work at any screen resolution or display scaling:

```json
{"steps": [{"action": "click", "target": "Submit button", "confidence": 0.97, "point": {"x": 366, "y": 347}}]}
```

`action` must be `"click"`, `x` and `y` must be numbers from 0 to 1000, and a request can have at most 10 steps.
`target` and `confidence` are optional. If any step is invalid, the whole request is rejected and nothing is
clicked.

## Requirements

* **Laptop:** Windows 10/11 (the primary target) or macOS, with Python 3.9 or later.
* **Phone:** Android 8.0 (API 26) or later.
* **To build the APK:** Android Studio, or a JDK 17+ plus the Android SDK with the Android 16 QPR2 platform (`android-36.1`). The Gradle wrapper is
  included.

## Laptop setup

```powershell
cd C:\path\to\ScreenLink\laptop
python -m pip install -r requirements.txt
python client.py
```

The console prints the laptop's IP address, the port (default **5001**), and a **pairing code**:

```
  ScreenLink laptop client
  Listening on port 5001
  Laptop IP:     192.168.1.20
  Paired phones: 0
  Pairing code:  482913
  Press Ctrl+C to stop.
```

Press **Ctrl+C** to stop the client at any time. That also cancels any typing in progress.

Options:

* `python client.py --port 5050` uses a different port.
* `python client.py --reset-pairing` forgets every paired phone.
* `laptop\config.json` overrides any default in `config.py`, for example `{"port": 5050, "max_click_steps": 5}`.

On **macOS**, give your terminal app *Screen Recording* and *Accessibility* permission (System Settings → Privacy &
Security). Without them, screenshots come out blank and typing or clicking does nothing.

### Finding the laptop's IP address

The client prints it at startup. You can also check it yourself:

```powershell
ipconfig
```

Use the **IPv4 Address** of the Wi-Fi adapter. It's usually `192.168.x.x`, `10.x.x.x` or `172.16-31.x.x`. Ignore
VPN and virtual adapters such as WSL, Hyper-V or VirtualBox.

### Windows Firewall

The first time `python` listens on the network, Windows may ask whether to allow it. Allowing it for all ports
works, but a rule limited to ScreenLink's port is tighter. Run this in an **administrator** PowerShell:

```powershell
New-NetFirewallRule -DisplayName "ScreenLink" -Direction Inbound -Protocol TCP -LocalPort 5001 -Action Allow -Profile Private,Public
```

Remove the rule later with `Remove-NetFirewallRule -DisplayName "ScreenLink"`. If your Wi-Fi is set to **Public**,
the rule needs the `Public` profile, as above. Only add it on networks you trust.

## Android app

### Build

```powershell
cd C:\path\to\ScreenLink\android
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat assembleDebug
```

The APK is written to `android\app\build\outputs\apk\debug\app-debug.apk`. If the SDK isn't found, create
`android\local.properties` containing `sdk.dir=C:/Users/<you>/AppData/Local/Android/Sdk`. Opening the `android`
folder in Android Studio also works.

Run the unit tests (the click-response parser) with `.\gradlew.bat testDebugUnitTest`.

### Install

Copy the APK to the phone and open it (you'll need to allow "install unknown apps"), or install it with ADB:

```powershell
adb install -r android\app\build\outputs\apk\debug\app-debug.apk
```

After installing, the app works on its own. USB and ADB are only needed for development.

### Pair the phone

1. Start the laptop client.
2. Open ScreenLink, enter the laptop's IP address and port, and tap **Connect**.
3. The status shows **Not paired**. Enter the pairing code from the laptop console and tap **Pair**.
4. The status changes to **Connected**.

The phone stores its token and the laptop stores a hash of it in `laptop\paired.json`, so you only pair once.
Restarting either device doesn't require pairing again. Each pairing code works once; a new code is printed after
every successful pairing. After 5 wrong codes, pairing is disabled until the client restarts.

### Use it

1. **Screenshot:** tap **Take screenshot**, then tap the image to zoom (pinch to zoom, drag to pan). **Share
   screenshot** opens Android's share sheet.
2. **Prompt:** choose General, Fill in the blank, Python, SQL, Email, Click or Custom. The Custom prompt can be
   edited and is saved automatically. Use **Copy prompt** or **Share prompt**. **Share screenshot + prompt** sends
   both, and also copies the prompt, because many apps ignore text that comes with an image.
3. **Response:** paste the AI's reply into **AI response**, using **Paste** or a long-press.
4. **Type on laptop:** click into the target window on the laptop first, then tap **Send text to laptop**. Typing
   starts after 1 second, at roughly 60 characters per second. Progress shows on the phone, and **Cancel typing**
   stops it immediately. Tick **Remove leading indentation** for code editors that auto-indent new lines.
5. **Click on laptop:** with a response to the Click prompt, the app lists the parsed points. **Execute clicks on
   laptop** clicks them in order.

The status line under the actions separates three stages: the request was sent ("Sending..."), the laptop accepted
it ("Laptop accepted job #3..."), and the final result the laptop reported ("Laptop typed all 120 characters",
"Typing cancelled after 40 of 120 characters", or an error).

## Troubleshooting

| Phone shows | Likely cause |
|---|---|
| *No response from IP:port* | The client isn't running, the IP is wrong, Windows Firewall is blocking the port, the devices are on different networks, or the Wi-Fi isolates clients (common on guest, public, university and hotel networks). |
| *Could not connect ... (ECONNREFUSED)* | The laptop is reachable, but nothing is listening on that port. Check the port, or start the client. |
| *No route to host* | The phone and laptop are on different networks or subnets. |
| *Something answered ... not the ScreenLink client* | Another program is using that port. Use `--port`. |
| *Not paired* | This phone's token is missing or was reset (`--reset-pairing`). Pair again. |
| *Pairing is locked* | Too many wrong codes. Restart the laptop client to get a new code. |

To check whether the network isolates clients, ping the phone's IP from the laptop (`ping <phone-ip>`). If that
fails while both are connected, use another network or a phone hotspot.

## Security limitations

* **Authentication:** every control endpoint requires a 256-bit random token, issued only in exchange for a
  one-time pairing code that is shown on the laptop's screen. Knowing the IP address isn't enough. The laptop
  stores only SHA-256 hashes of tokens, and never logs tokens or the text you send.
* **Plain HTTP:** traffic between the phone and laptop is not encrypted. Someone else on the same Wi-Fi who can
  capture packets could see screenshots, typed text and the token, and then reuse the token. Use ScreenLink only on
  networks you trust (home Wi-Fi or your own hotspot). If you suspect the token leaked, run
  `python client.py --reset-pairing`.
* **Cleartext on Android:** the app allows cleartext HTTP (`res/xml/network_security_config.xml`), because Android
  can't limit that permission to a user-entered private IP address.
* **Local network only:** don't port-forward 5001 or expose the client to the internet. The firewall rule above
  only opens the port to inbound connections on the networks you choose.
* **Limited actions:** the client only takes screenshots, types the text you send and clicks validated points. It
  never runs code or shell commands from a response. Every action starts from a button you press in the app. Text
  is limited to 20,000 characters, request bodies to 64 KB, and click requests to 10 steps.
