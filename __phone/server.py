import logging
import signal
import sys

import requests

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    Response
)

from config import load_config

from logger import (
    log,
    log_error,
    console,
    console_error
)

from network import get_phone_ip

from device_manager import (
    DeviceManager
)

from screenshot_manager import (
    ScreenshotManager
)


app = Flask(__name__)


logging.getLogger(
    "werkzeug"
).setLevel(
    logging.ERROR
)


config = load_config()


PORT = int(
    config["server_port"]
)

HEARTBEAT_TIMEOUT = int(
    config["heartbeat_timeout"]
)

SCREENSHOT_DIRECTORY = (
    config["screenshot_directory"]
)


device_manager = DeviceManager(
    HEARTBEAT_TIMEOUT
)


screenshot_manager = (
    ScreenshotManager(
        SCREENSHOT_DIRECTORY
    )
)


@app.route(
    "/",
    methods=["GET"]
)
def index():

    log(
        "Web interface opened"
    )

    return render_template(
        "index.html"
    )


@app.route(
    "/status",
    methods=["GET"]
)
def status():

    log(
        "Phone status requested"
    )

    return jsonify({

        "success": True,

        "service": "ScreenLink",

        "status": "online",

        "ip": get_phone_ip(),

        "port": PORT

    })


@app.route(
    "/register",
    methods=["POST"]
)
def register():

    log(
        "Laptop registration request received"
    )

    try:

        data = request.get_json()

        if not data:

            log(
                "Registration rejected: "
                "missing JSON data"
            )

            return jsonify({

                "success": False,

                "message":
                    "Missing registration data"

            }), 400


        device_name = data.get(
            "device_name"
        )

        ip = data.get(
            "ip"
        )

        port = data.get(
            "port"
        )


        if not device_name:

            log(
                "Registration rejected: "
                "missing device name"
            )

            return jsonify({

                "success": False,

                "message":
                    "Missing laptop name"

            }), 400


        if not ip:

            log(
                "Registration rejected: "
                "missing laptop IP"
            )

            return jsonify({

                "success": False,

                "message":
                    "Missing laptop IP"

            }), 400


        if not port:

            log(
                "Registration rejected: "
                "missing laptop port"
            )

            return jsonify({

                "success": False,

                "message":
                    "Missing laptop port"

            }), 400


        log(
            f"Laptop -> {device_name}"
        )

        log(
            f"Laptop IP -> {ip}"
        )

        log(
            f"Laptop port -> {port}"
        )


        device_manager.register(

            device_name,

            ip,

            port

        )


        log(
            "Laptop registration successful"
        )


        console(
            "Laptop connected"
        )


        return jsonify({

            "success": True,

            "message":
                "Laptop registered successfully"

        })


    except Exception as e:

        log_error(
            "Registration failed: "
            + str(e)
        )

        console_error(
            "Could not register laptop."
        )

        return jsonify({

            "success": False,

            "message":
                "Registration failed"

        }), 500


@app.route(
    "/heartbeat",
    methods=["POST"]
)
def heartbeat():

    try:

        data = request.get_json()

        if not data:

            log(
                "Heartbeat rejected: "
                "missing JSON data"
            )

            return jsonify({

                "success": False,

                "message":
                    "Missing heartbeat data"

            }), 400


        device_name = data.get(
            "device_name"
        )

        ip = data.get(
            "ip"
        )

        port = data.get(
            "port"
        )


        updated = (
            device_manager.heartbeat(

                device_name,

                ip,

                port

            )
        )


        if not updated:

            log(
                f"Heartbeat rejected: "
                f"unknown laptop -> "
                f"{device_name}"
            )

            return jsonify({

                "success": False,

                "message":
                    "Laptop not registered"

            }), 404


        log(
            f"Heartbeat received -> "
            f"{device_name}"
        )


        return jsonify({

            "success": True,

            "message":
                "Heartbeat received"

        })


    except Exception as e:

        log_error(
            "Heartbeat failed: "
            + str(e)
        )

        return jsonify({

            "success": False,

            "message":
                "Heartbeat failed"

        }), 500


@app.route(
    "/device",
    methods=["GET"]
)
def device():

    log(
        "Laptop status requested"
    )

    laptop = (
        device_manager.get_status()
    )

    return jsonify({

        "success": True,

        "device":
            laptop

    })


@app.route(
    "/screenshot",
    methods=["GET"]
)
def screenshot():

    log(
        "Screenshot request received"
    )

    device = (
        device_manager.get_device()
    )


    if not device:

        log(
            "Screenshot failed: "
            "no laptop registered"
        )

        return jsonify({

            "success": False,

            "message":
                "No laptop connected"

        }), 404


    if not device_manager.is_online():

        log(
            "Screenshot failed: "
            "laptop offline"
        )

        return jsonify({

            "success": False,

            "message":
                "Laptop is offline"

        }), 503


    result = (
        screenshot_manager.capture(
            device
        )
    )


    if not result:

        log(
            "Screenshot capture failed"
        )

        return jsonify({

            "success": False,

            "message":
                "Screenshot failed"

        }), 500


    try:

        log(
            f"Returning screenshot -> "
            f"{result['filename']}"
        )

        return Response(

            result["data"],

            mimetype="image/png"

        )


    except Exception as e:

        log_error(
            "Failed to return screenshot: "
            + str(e)
        )

        console_error(
            "Could not send screenshot."
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to send screenshot"

        }), 500


@app.route(
    "/type",
    methods=["POST"]
)
def type_device():

    log(
        "Typing request received"
    )

    device = (
        device_manager.get_device()
    )


    if not device:

        log(
            "Typing failed: "
            "no laptop registered"
        )

        return jsonify({

            "success": False,

            "message":
                "No laptop connected"

        }), 404


    if not device_manager.is_online():

        log(
            "Typing failed: "
            "laptop offline"
        )

        return jsonify({

            "success": False,

            "message":
                "Laptop is offline"

        }), 503


    try:

        data = request.get_json()


        if not data:

            return jsonify({

                "success": False,

                "message":
                    "Missing text data"

            }), 400


        text = data.get(
            "text"
        )


        if text is None:

            return jsonify({

                "success": False,

                "message":
                    "Missing text"

            }), 400


        url = (
            f"http://{device['ip']}:"
            f"{device['port']}"
            f"/type"
        )


        log(
            f"Sending typing request -> "
            f"{url}"
        )

        log(
            f"Typing text length -> "
            f"{len(text)}"
        )


        response = requests.post(

            url,

            json={
                "text": text
            },

            timeout=5

        )


        log(
            f"Laptop typing response -> "
            f"{response.status_code}"
        )


        if response.status_code == 200:

            console(
                "Typing started"
            )


        return (

            response.text,

            response.status_code,

            {
                "Content-Type":
                    "application/json"
            }

        )


    except Exception as e:

        log_error(
            "Typing request failed: "
            + str(e)
        )

        console_error(
            "Could not start typing."
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to start typing"

        }), 500


@app.route(
    "/stop-type",
    methods=["POST"]
)
def stop_type():

    log(
        "Stop typing request received"
    )

    device = (
        device_manager.get_device()
    )


    if not device:

        return jsonify({

            "success": False,

            "message":
                "No laptop connected"

        }), 404


    if not device_manager.is_online():

        return jsonify({

            "success": False,

            "message":
                "Laptop is offline"

        }), 503


    try:

        url = (
            f"http://{device['ip']}:"
            f"{device['port']}"
            f"/stop-type"
        )


        log(
            f"Sending stop typing request -> "
            f"{url}"
        )


        response = requests.post(

            url,

            timeout=5

        )


        log(
            f"Laptop stop typing response -> "
            f"{response.status_code}"
        )


        if response.status_code == 200:

            console(
                "Typing stopped"
            )


        return (

            response.text,

            response.status_code,

            {
                "Content-Type":
                    "application/json"
            }

        )


    except Exception as e:

        log_error(
            "Stop typing request failed: "
            + str(e)
        )

        console_error(
            "Could not stop typing."
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to stop typing"

        }), 500


def shutdown(
    signum=None,
    frame=None
):

    log(
        "ScreenLink phone server shutting down"
    )

    console(
        "ScreenLink stopped"
    )

    sys.exit(0)


if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        shutdown
    )

    signal.signal(
        signal.SIGTERM,
        shutdown
    )


    phone_ip = get_phone_ip()


    print()
    print(
        f"Phone IP: {phone_ip}"
    )
    print()


    log(
        "========================================"
    )

    log(
        "ScreenLink phone server starting"
    )

    log(
        f"Phone IP -> {phone_ip}"
    )

    log(
        f"HTTP port -> {PORT}"
    )

    log(
        f"Screenshot directory -> "
        f"{SCREENSHOT_DIRECTORY}"
    )

    log(
        "Waiting for laptop registration"
    )


    try:

        app.run(

            host="0.0.0.0",

            port=PORT,

            debug=False,

            use_reloader=False,

            threaded=True

        )


    except KeyboardInterrupt:

        shutdown()


    except Exception as e:

        log_error(
            "Server crashed: "
            + str(e)
        )

        console_error(
            "Phone server stopped unexpectedly."
        )

        shutdown()