import json
import os
import time

from logger import log, log_error


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

DEVICE_FILE = os.path.join(
    DATA_DIR,
    "devices.json"
)


class DeviceManager:

    def __init__(self, heartbeat_timeout):

        self.heartbeat_timeout = heartbeat_timeout

        self.device = None

        self.load()

    def load(self):

        os.makedirs(
            DATA_DIR,
            exist_ok=True
        )

        if not os.path.exists(
            DEVICE_FILE
        ):

            self.device = None

            self.save()

            return

        try:

            with open(
                DEVICE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(data, dict) and data:

                if "name" in data:

                    self.device = data

                else:

                    devices = list(data.values())

                    if devices:

                        self.device = devices[0]

                    else:

                        self.device = None

            else:

                self.device = None

            if self.device:

                log(
                    "Loaded registered laptop -> "
                    f"{self.device['name']}"
                )

        except Exception as e:

            log_error(
                "Failed to load device: "
                + str(e)
            )

            self.device = None

    def save(self):

        os.makedirs(
            DATA_DIR,
            exist_ok=True
        )

        try:

            with open(
                DEVICE_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.device or {},
                    f,
                    indent=4
                )

        except Exception as e:

            log_error(
                "Failed to save device: "
                + str(e)
            )

    def register(
        self,
        device_name,
        ip,
        port
    ):

        existing = (
            self.device is not None
        )

        self.device = {

            "name": device_name,

            "ip": ip,

            "port": int(port),

            "last_seen": time.time()
        }

        self.save()

        if existing:

            log(
                f"Laptop re-registered -> "
                f"{device_name} "
                f"({ip}:{port})"
            )

        else:

            log(
                f"Laptop registered -> "
                f"{device_name} "
                f"({ip}:{port})"
            )

    def heartbeat(
        self,
        device_name,
        ip=None,
        port=None
    ):

        if self.device is None:

            return False

        if (
            self.device["name"]
            != device_name
        ):

            return False

        self.device["last_seen"] = (
            time.time()
        )

        if ip:
            self.device["ip"] = ip

        if port:
            self.device["port"] = int(port)

        self.save()

        return True

    def get_device(self):

        return self.device

    def is_online(self):

        if self.device is None:

            return False

        elapsed = (
            time.time()
            - self.device["last_seen"]
        )

        return (
            elapsed
            <= self.heartbeat_timeout
        )

    def get_status(self):

        if self.device is None:

            return None

        return {

            "name":
                self.device["name"],

            "ip":
                self.device["ip"],

            "port":
                self.device["port"],

            "online":
                self.is_online(),

            "last_seen_seconds":
                round(
                    time.time()
                    - self.device["last_seen"],
                    1
                )
        }

    def remove_device(self):

        if self.device is not None:

            name = self.device["name"]

            self.device = None

            self.save()

            log(
                f"Laptop removed -> {name}"
            )

            return True

        return False