import subprocess
import re

from logger import log_error


PREFERRED_INTERFACES = [
    "wlan2",
    "wlan0",
    "rndis0",
    "usb0"
]


def get_phone_ip():

    try:

        result = subprocess.run(
            ["ifconfig"],
            capture_output=True,
            text=True,
            timeout=5
        )

        output = (
            result.stdout
            + result.stderr
        )

        for interface in PREFERRED_INTERFACES:

            pattern = (
                rf"(?m)^{re.escape(interface)}:.*?"
                rf"\binet\s+"
                rf"(\d+\.\d+\.\d+\.\d+)"
            )

            match = re.search(
                pattern,
                output,
                re.DOTALL
            )

            if match:

                ip = match.group(1)

                if ip != "127.0.0.1":

                    return ip

    except Exception as e:

        log_error(
            "Unable to determine phone IP: "
            + str(e)
        )

    return "UNKNOWN"