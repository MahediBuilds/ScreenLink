# Security policy

ScreenLink lets a phone control a computer, so security reports are taken seriously.

## Reporting a vulnerability

Please **don't open a public issue**. Use GitHub's private reporting instead: go to the repository's
**Security** tab and choose **Report a vulnerability**. Include the affected version, steps to reproduce, and the
impact you expect.

You can expect an acknowledgement within a week. Please give us a reasonable amount of time to fix the issue
before you disclose it publicly.

## Supported versions

Only the latest release gets security fixes.

## Known limitations (by design)

These are documented trade-offs, not vulnerabilities:

- Traffic between the phone and laptop is plain HTTP on the local network. Anyone on the same network who can
  capture packets can read screenshots, typed text and the pairing token. Use ScreenLink only on trusted
  networks.
- The Android app allows cleartext HTTP, because Android can't limit that permission to a user-entered private
  IP address.
- After pairing, anyone holding a phone's token can control the laptop while the client is running. Run
  `python client.py --reset-pairing` to revoke all tokens.
