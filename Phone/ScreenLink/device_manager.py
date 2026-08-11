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

        self.heartbeat_timeout = (
            heartbeat_timeout
        )

        self.devices = {}

        self.load()

    def load(self):

        os.makedirs(
            DATA_DIR,
            exist_ok=True
        )

        if not os.path.exists(
            DEVICE_FILE
        ):

            self.devices = {}

            self.save()

            return

        try:

            with open(
                DEVICE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.devices = json.load(f)

            log(
                f"Loaded {len(self.devices)} "
                f"registered device(s)"
            )

        except Exception as e:

            log_error(
                "Failed to load devices: "
                + str(e)
            )

            self.devices = {}

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
                    self.devices,
                    f,
                    indent=4
                )

        except Exception as e:

            log_error(
                "Failed to save devices: "
                + str(e)
            )

    def register(
        self,
        device_name,
        ip,
        port
    ):

        existing = (
            device_name
            in self.devices
        )

        self.devices[device_name] = {

            "name": device_name,

            "ip": ip,

            "port": int(port),

            "last_seen": time.time()
        }

        self.save()

        if existing:

            log(
                f"Device re-registered -> "
                f"{device_name} "
                f"({ip}:{port})"
            )

        else:

            log(
                f"Device registered -> "
                f"{device_name} "
                f"({ip}:{port})"
            )

    def heartbeat(
        self,
        device_name,
        ip=None,
        port=None
    ):

        if device_name not in self.devices:

            return False

        device = (
            self.devices[device_name]
        )

        device["last_seen"] = time.time()

        if ip:
            device["ip"] = ip

        if port:
            device["port"] = int(port)

        self.save()

        return True

    def add_manual_device(
        self,
        device_name,
        ip,
        port
    ):

        self.devices[device_name] = {

            "name": device_name,

            "ip": ip,

            "port": int(port),

            "last_seen": time.time()
        }

        self.save()

        log(
            f"Manual device added -> "
            f"{device_name} "
            f"({ip}:{port})"
        )

    def get_device(
        self,
        device_name
    ):

        return self.devices.get(
            device_name
        )

    def is_online(self, device):

        elapsed = (
            time.time()
            - device["last_seen"]
        )

        return (
            elapsed
            <= self.heartbeat_timeout
        )

    def get_devices(self):

        result = []

        for device in self.devices.values():

            result.append({

                "name": device["name"],

                "ip": device["ip"],

                "port": device["port"],

                "online": self.is_online(
                    device
                ),

                "last_seen_seconds":
                    round(
                        time.time()
                        - device["last_seen"],
                        1
                    )
            })

        return result

    def remove_device(
        self,
        device_name
    ):

        if device_name in self.devices:

            del self.devices[
                device_name
            ]

            self.save()

            log(
                f"Device removed -> "
                f"{device_name}"
            )

            return True

        return False