from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    Response
)

import signal
import sys
import requests

from config import load_config

from logger import (
    log,
    log_error,
    get_log_file
)

from network import get_phone_ip

from device_manager import (
    DeviceManager
)

from screenshot_manager import (
    ScreenshotManager
)


app = Flask(__name__)

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
        "Phone server status requested"
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

            return jsonify({

                "success": False,

                "message":
                    "Missing JSON data"

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

            return jsonify({

                "success": False,

                "message":
                    "Missing device name"

            }), 400

        if not ip:

            return jsonify({

                "success": False,

                "message":
                    "Missing device IP"

            }), 400

        if not port:

            return jsonify({

                "success": False,

                "message":
                    "Missing device port"

            }), 400

        device_manager.register(
            device_name,
            ip,
            port
        )

        return jsonify({

            "success": True,

            "message":
                "Laptop registered successfully",

            "device": {

                "name":
                    device_name,

                "ip":
                    ip,

                "port":
                    int(port)

            }

        })

    except Exception as e:

        log_error(
            "Registration failed: "
            + str(e)
        )

        return jsonify({

            "success": False,

            "message":
                str(e)

        }), 500


@app.route(
    "/heartbeat",
    methods=["POST"]
)
def heartbeat():

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,

                "message":
                    "Missing JSON data"

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

            return jsonify({

                "success": False,

                "message":
                    "Missing device name"

            }), 400

        updated = device_manager.heartbeat(

            device_name,

            ip,

            port

        )

        if not updated:

            log(
                f"Heartbeat from unknown "
                f"laptop -> {device_name}"
            )

            return jsonify({

                "success": False,

                "message":
                    "Laptop not registered"

            }), 404

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
                str(e)

        }), 500


@app.route(
    "/device",
    methods=["GET"]
)
def device():

    laptop = device_manager.get_status()

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
        "========================================"
    )

    log(
        "Screenshot request received"
    )

    device = device_manager.get_device()

    if not device:

        log(
            "Screenshot failed: "
            "no laptop registered"
        )

        return jsonify({

            "success": False,

            "message":
                "No laptop registered"

        }), 404

    if not device_manager.is_online():

        log(
            "Screenshot failed: "
            "laptop is offline"
        )

        return jsonify({

            "success": False,

            "message":
                "Laptop is offline"

        }), 503

    result = screenshot_manager.capture(
        device
    )

    if not result:

        return jsonify({

            "success": False,

            "message":
                "Screenshot failed"

        }), 500

    return Response(

        result["data"],

        mimetype="image/png"

    )


@app.route(
    "/type",
    methods=["POST"]
)
def type_device():

    log(
        "========================================"
    )

    log(
        "Typing request received"
    )

    device = device_manager.get_device()

    if not device:

        return jsonify({

            "success": False,

            "message":
                "No laptop registered"

        }), 404

    if not device_manager.is_online():

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
                    "Missing JSON data"

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

        return jsonify({

            "success": False,

            "message":
                str(e)

        }), 500


@app.route(
    "/stop-type",
    methods=["POST"]
)
def stop_type():

    log(
        "Stop typing request received"
    )

    device = device_manager.get_device()

    if not device:

        return jsonify({

            "success": False,

            "message":
                "No laptop registered"

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

        return jsonify({

            "success": False,

            "message":
                str(e)

        }), 500


def shutdown(
    signum=None,
    frame=None
):

    log(
        "ScreenLink phone server shutting down"
    )

    log(
        "Goodbye."
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
    print("=" * 45)
    print("       SCREENLINK PHONE SERVER")
    print("=" * 45)

    print(
        f"Phone IP       : {phone_ip}"
    )

    print(
        f"Server Address : "
        f"http://{phone_ip}:{PORT}"
    )

    print(
        f"HTTP Port      : {PORT}"
    )

    print(
        f"Screenshot Dir : "
        f"{SCREENSHOT_DIRECTORY}"
    )

    print(
        f"Log File       : "
        f"{get_log_file()}"
    )

    print("=" * 45)
    print(
        "Waiting for laptop..."
    )
    print("=" * 45)

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
        f"Log file -> "
        f"{get_log_file()}"
    )

    try:

        app.run(

            host="0.0.0.0",

            port=PORT,

            debug=False,

            use_reloader=False

        )

    except KeyboardInterrupt:

        shutdown()

    except Exception as e:

        log_error(
            "Server crashed: "
            + str(e)
        )

        shutdown()