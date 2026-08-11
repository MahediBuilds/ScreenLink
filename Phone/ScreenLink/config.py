import json
import os

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CONFIG_DIR = os.path.join(
    BASE_DIR,
    "config"
)

CONFIG_FILE = os.path.join(
    CONFIG_DIR,
    "config.json"
)

DEFAULT_CONFIG = {
    "server_port": 5000,
    "heartbeat_timeout": 30,
    "screenshot_directory": "~/storage/pictures/ScreenLink"
}


def ensure_config():
    os.makedirs(
        CONFIG_DIR,
        exist_ok=True
    )

    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)


def load_config():
    ensure_config()

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            config = json.load(f)

        for key, value in DEFAULT_CONFIG.items():

            if key not in config:
                config[key] = value

        return config

    except Exception:

        save_config(DEFAULT_CONFIG)

        return DEFAULT_CONFIG.copy()


def save_config(config):

    os.makedirs(
        CONFIG_DIR,
        exist_ok=True
    )

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            config,
            f,
            indent=4
        )