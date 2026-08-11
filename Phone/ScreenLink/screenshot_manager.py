import os
import subprocess

import requests

from logger import log, log_error


class ScreenshotManager:

    def __init__(self, screenshot_directory):
        self.directory = os.path.expanduser(
            screenshot_directory
        )

        os.makedirs(
            self.directory,
            exist_ok=True
        )

    def capture(self, device):
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

            timestamp = response.headers.get(
                "X-ScreenLink-Timestamp"
            )

            filename = response.headers.get(
                "X-ScreenLink-Filename"
            )

            if not timestamp:
                log(
                    "Laptop did not provide "
                    "screenshot timestamp"
                )

                return None

            if not filename:
                filename = (
                    f"{device['name']}_"
                    f"{timestamp}.png"
                )
            else:
                filename = (
                    f"{device['name']}_"
                    f"{filename}"
                )

            path = os.path.join(
                self.directory,
                filename
            )

            with open(path, "wb") as f:
                f.write(
                    response.content
                )

            size = os.path.getsize(
                path
            )

            log(
                f"Screenshot timestamp -> "
                f"{timestamp}"
            )

            log(
                f"Screenshot saved -> "
                f"{path}"
            )

            log(
                f"Screenshot size -> "
                f"{size} bytes"
            )

            self.scan_media(path)

            return {
                "filename": filename,
                "path": path,
                "timestamp": timestamp,
                "size": size,
                "data": response.content
            }

        except Exception as e:
            log_error(
                "Screenshot request failed: "
                + str(e)
            )

            return None

    def scan_media(self, path):
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