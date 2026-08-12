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

    def __init__(
        self,
        heartbeat_timeout
    ):

        self.heartbeat_timeout = (
            heartbeat_timeout
        )

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


            self.device = None


            if isinstance(
                data,
                dict
            ):

                # New single-device format
                if self._is_valid_device(
                    data
                ):

                    self.device = (
                        self._normalize_device(
                            data
                        )
                    )


                # Old multi-device format
                else:

                    for value in (
                        data.values()
                    ):

                        if isinstance(
                            value,
                            dict
                        ) and self._is_valid_device(
                            value
                        ):

                            self.device = (
                                self._normalize_device(
                                    value
                                )
                            )

                            break


            elif isinstance(
                data,
                list
            ):

                # Handle any old list format
                for value in data:

                    if isinstance(
                        value,
                        dict
                    ) and self._is_valid_device(
                        value
                    ):

                        self.device = (
                            self._normalize_device(
                                value
                            )
                        )

                        break


            if self.device:

                log(
                    "Registered laptop loaded -> "
                    f"{self.device['name']}"
                )

            else:

                log(
                    "No valid registered laptop found"
                )


            # Rewrite the file using the new
            # clean single-device format.
            self.save()


        except Exception as e:

            log_error(
                "Failed to load devices: "
                + str(e)
            )


            self.device = None

            self.save()


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

                    self.device,

                    f,

                    indent=4

                )


        except Exception as e:

            log_error(
                "Failed to save devices: "
                + str(e)
            )


    def _is_valid_device(
        self,
        device
    ):

        if not isinstance(
            device,
            dict
        ):

            return False


        required = (
            "name",
            "ip",
            "port",
            "last_seen"
        )


        return all(
            key in device
            for key in required
        )


    def _normalize_device(
        self,
        device
    ):

        return {

            "name":
                str(
                    device["name"]
                ),

            "ip":
                str(
                    device["ip"]
                ),

            "port":
                int(
                    device["port"]
                ),

            "last_seen":
                float(
                    device["last_seen"]
                )

        }


    def register(
        self,
        device_name,
        ip,
        port
    ):

        replacing = (
            self.device is not None
        )


        self.device = {

            "name":
                str(
                    device_name
                ),

            "ip":
                str(
                    ip
                ),

            "port":
                int(
                    port
                ),

            "last_seen":
                time.time()

        }


        self.save()


        if replacing:

            log(
                "Laptop re-registered -> "
                f"{device_name} "
                f"({ip}:{port})"
            )

        else:

            log(
                "Laptop registered -> "
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

            self.device["ip"] = str(
                ip
            )


        if port:

            self.device["port"] = int(
                port
            )


        self.save()


        return True


    def add_manual_device(
        self,
        device_name,
        ip,
        port
    ):

        self.device = {

            "name":
                str(
                    device_name
                ),

            "ip":
                str(
                    ip
                ),

            "port":
                int(
                    port
                ),

            "last_seen":
                time.time()

        }


        self.save()


        log(
            "Laptop manually added -> "
            f"{device_name} "
            f"({ip}:{port})"
        )


    def get_device(
        self,
        device_name
    ):

        if self.device is None:

            return None


        if (
            self.device["name"]
            != device_name
        ):

            return None


        return self.device


    def is_online(
        self,
        device
    ):

        if not isinstance(
            device,
            dict
        ):

            return False


        if "last_seen" not in device:

            return False


        elapsed = (

            time.time()

            - float(
                device["last_seen"]
            )

        )


        return (
            elapsed
            <= self.heartbeat_timeout
        )


    def get_devices(self):

        if self.device is None:

            return []


        return [{

            "name":
                self.device["name"],

            "ip":
                self.device["ip"],

            "port":
                self.device["port"],

            "online":
                self.is_online(
                    self.device
                ),

            "last_seen_seconds":
                round(

                    time.time()
                    - self.device["last_seen"],

                    1

                )

        }]


    def remove_device(
        self,
        device_name
    ):

        if self.device is None:

            return False


        if (
            self.device["name"]
            != device_name
        ):

            return False


        self.device = None


        self.save()


        log(
            f"Laptop removed -> "
            f"{device_name}"
        )


        return True