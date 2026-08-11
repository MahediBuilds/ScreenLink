import os
import subprocess
import time

import requests

from logger import log, log_error


class ScreenshotManager:

    def __init__(
        self,
        screenshot_directory
    ):

        self.directory = os.path.expanduser(
            screenshot_directory
        )

        os.makedirs(
            self.directory,
            exist_ok=True
        )

    def capture(
        self,
        device
    ):

        ip = device["ip"]
        port = device["port"]

        url = (
            f"http://{ip}:{port}"
            f"/screenshot"
        )

        log(
            f"Screenshot request -> "
            f"{url}"
        )

        try:

            response = requests.get(
                url,
                timeout=30
            )

            log(
                f"Laptop screenshot response -> "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                log(
                    "Laptop failed to capture "
                    "screenshot"
                )

                return None

            timestamp = time.strftime(
                "%Y%m%d_%H%M%S"
            )

            filename = (
                f"{device['name']}_"
                f"{timestamp}.png"
            )

            path = os.path.join(
                self.directory,
                filename
            )

            with open(
                path,
                "wb"
            ) as f:

                f.write(
                    response.content
                )

            size = os.path.getsize(
                path
            )

            log(
                f"Screenshot saved -> {path}"
            )

            log(
                f"Screenshot size -> "
                f"{size} bytes"
            )

            self.scan_media(path)

            return {

                "filename": filename,

                "path": path,

                "size": size,

                "data":
                    response.content
            }

        except Exception as e:

            log_error(
                "Screenshot request failed: "
                + str(e)
            )

            return None

    def scan_media(
        self,
        path
    ):

        try:

            subprocess.run(
                [
                    "termux-media-scan",
                    path
                ],
                timeout=5
            )

            log(
                f"Media scan completed -> "
                f"{path}"
            )

        except Exception as e:

            log(
                "Media scan failed -> "
                + str(e)
            )