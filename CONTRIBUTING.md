# Contributing to ScreenLink

Thanks for helping! Bug reports, fixes, new prompt templates and documentation improvements are all welcome.

## Reporting a bug

Open an issue that includes:

- what you did, what you expected, and what happened (include the exact error text from the app or console);
- your laptop OS and Python version, and your phone model and Android version;
- whether the phone and laptop are on home Wi-Fi, a hotspot or another network.

Never paste pairing codes, tokens or the contents of `laptop/paired.json`.

For security problems, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Development setup

**Laptop client** (Python 3.9+):

```powershell
cd laptop
python -m pip install -r requirements.txt pytest
python client.py
```

**Android app:** open `android/` in Android Studio, or see the [Android guide](android/README.md) for
command-line builds.

## Before opening a pull request

Run both test suites. Both must pass:

```powershell
python -m pytest tests                                   # from the repository root
cd android; .\gradlew.bat testDebugUnitTest assembleDebug
```

- Keep pull requests focused: one fix or feature per PR.
- Follow the style of the surrounding code (Kotlin: official style; Python: PEP 8, 120-column lines).
- Add or update tests when you change behavior. Laptop tests must use the fake desktop and keyboard and never
  really type or click.
- Update the relevant README when you change setup steps, the API or the UI.
- Keep it simple. ScreenLink deliberately has no cloud backend, accounts, AI API calls or extra frameworks.

## Adding a prompt template

Add a `.txt` file to `android/app/src/main/assets/prompts/`. The file name becomes the tab name (`_` shows as a
space). Say in the prompt exactly what format the answer must be in: plain text for **Send text to laptop**, or
the JSON click format (see `GUI.txt`) for **Execute clicks on laptop**.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
