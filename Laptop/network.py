import socket

from Laptop.logger import log, log_error


def get_local_ip():

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    try:

        sock.connect(
            ("8.8.8.8", 80)
        )

        ip = sock.getsockname()[0]

        return ip

    except Exception as e:

        log_error(
            "Unable to determine local IP: "
            + str(e)
        )

        return "127.0.0.1"

    finally:

        sock.close()