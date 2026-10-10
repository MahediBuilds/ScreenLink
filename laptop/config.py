"""ScreenLink laptop client settings.

Defaults live here. To override any of them, create laptop/config.json
containing only the keys you want to change, e.g. {"port": 5050}.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PAIRED_FILE = os.path.join(BASE_DIR, "paired.json")

DEFAULTS = {
    # Network
    "host": "0.0.0.0",          # interface to listen on (0.0.0.0 = all)
    "port": 5001,
    "max_body_bytes": 64 * 1024,
    # Pairing
    "pairing_code_digits": 6,
    "max_pairing_attempts": 5,   # wrong codes before pairing is disabled until restart
    # Screenshots
    "jpeg_quality": 80,
    # Text entry
    "max_text_chars": 20000,
    "type_start_delay": 1.0,     # seconds before typing begins (speed and pauses: see typer.py)
    # Clicks
    "max_click_steps": 10,
    "click_interval": 0.25,      # seconds between clicks
}


def load_config(path=CONFIG_FILE):
    config = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        unknown = set(overrides) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"Unknown keys in {path}: {', '.join(sorted(unknown))}")
        config.update(overrides)
    return config
