# ScreenLink Android app

A native Android app (Kotlin, Jetpack Compose) that connects to the ScreenLink laptop client on your local
network.

- **Application ID:** `com.mahedibuilds.screenlink`
- **Minimum Android version:** 8.0 (API 26); targets API 36
- **Dependencies:** Jetpack Compose (Material 3), `activity-compose` and `lifecycle-viewmodel-compose`.
  Networking, clipboard, sharing and storage use Android's built-in APIs.

## Project layout

```
android/
├── app/
│   ├── build.gradle.kts
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml
│       │   ├── assets/prompts/          ← built-in prompt templates (.txt)
│       │   ├── java/com/mahedibuilds/screenlink/
│       │   │   ├── MainActivity.kt      UI (Compose)
│       │   │   ├── ScreenLinkViewModel.kt  state, connection, actions, saved settings
│       │   │   ├── LaptopApi.kt         HTTP client and error messages
│       │   │   ├── Prompts.kt           prompt loading/ordering, click-response parser
│       │   │   └── Sharing.kt           clipboard, share sheet, save to gallery
│       │   └── res/                     icon, strings, network-security config
│       └── test/                        JVM unit tests
├── build.gradle.kts, settings.gradle.kts, gradle.properties
└── gradlew, gradlew.bat, gradle/wrapper/
```

## Build

You need a JDK 17+ (Android Studio's bundled JBR works) and the Android SDK with the **Android 16 QPR2
(`android-36.1`)** platform. The easiest setup is to open the `android/` folder in Android Studio. From the
command line on Windows:

```powershell
cd android
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat assembleDebug          # → app\build\outputs\apk\debug\app-debug.apk
.\gradlew.bat testDebugUnitTest      # unit tests
```

On macOS and Linux, use `./gradlew`. If Gradle can't find the SDK, create `android/local.properties` containing
`sdk.dir=C:/Users/<you>/AppData/Local/Android/Sdk` (or your SDK path). The file is git-ignored.

### Release builds

```powershell
.\gradlew.bat assembleRelease        # → app\build\outputs\apk\release\app-release.apk
```

Release builds are shrunk with R8 (about 1 MB instead of about 10 MB for debug). They're signed only if
`android/keystore.properties` exists:

```properties
storeFile=C:/path/to/your-release-key.jks
storePassword=...
keyAlias=...
keyPassword=...
```

Without that file, `assembleRelease` produces an unsigned APK, which you'd have to sign yourself before
installing. `keystore.properties`, `*.jks` and `*.apk` are git-ignored. Never commit a signing key.

Android only installs an update if it's signed with the same key as the installed app. A debug build and a
release build can't replace each other: uninstall one before installing the other (this clears the app's saved
settings).

## Install

Copy the APK to the phone and open it, or install it over USB with debugging enabled:

```powershell
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

## Prompts

Each `.txt` file in `app/src/main/assets/prompts/` becomes a prompt tab, and its text is the exact prompt.

- The tab name is the file name without `.txt`, with `_` and `-` shown as spaces.
- Order: **General**, **Python**, **GUI**, then the others alphabetically (ignoring case), then **Custom**.
- Empty files are skipped. `Custom.txt` is ignored, because Custom is always the editable in-app tab.
- Prompts are bundled into the APK, so edits take effect after you rebuild and reinstall. The tabs are rebuilt
  from the bundled files each time the app starts.
- The Custom prompt, the last selected tab, the laptop address and the pairing token are saved in the app's
  private preferences. They survive app updates, but uninstalling deletes them.

## Network security

The app talks to the laptop over plain HTTP at a user-entered private IP address. Android blocks cleartext
traffic by default and can't scope an exception to an IP range, so `res/xml/network_security_config.xml` allows
cleartext. Every control request is authenticated with the pairing token; see the security notes in the
[main README](../README.md#security).
