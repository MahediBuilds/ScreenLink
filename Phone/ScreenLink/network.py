import subprocess
import re

from logger import log_error


def get_phone_ip():

    try:

        result = subprocess.run(
            ["ifconfig"],
            capture_output=True,
            text=True
        )

        output = (
            result.stdout
            + result.stderr
        )

        match = re.search(
            r"rndis0:.*?inet "
            r"(\d+\.\d+\.\d+\.\d+)",
            output,
            re.DOTALL
        )

        if match:

            return match.group(1)

    except Exception as e:

        log_error(
            "Unable to determine phone IP: "
            + str(e)
        )

    return "UNKNOWN"