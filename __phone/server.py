from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    Response
)

import signal
import sys

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

        "success":
            True,

        "service":
            "ScreenLink",

        "status":
            "online",

        "ip":
            get_phone_ip(),

        "port":
            PORT

    })


@app.route(
    "/register",
    methods=["POST"]
)
def register():

    log(
        "Registration request received"
    )


    try:

        data = request.get_json()


        if not data:

            return jsonify({

                "success":
                    False,

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

                "success":
                    False,

                "message":
                    "Missing device name"

            }), 400


        if not ip:

            return jsonify({

                "success":
                    False,

                "message":
                    "Missing device IP"

            }), 400


        if not port:

            return jsonify({

                "success":
                    False,

                "message":
                    "Missing device port"

            }), 400


        device_manager.register(

            device_name,

            ip,

            port

        )


        log(
            f"Device registered -> "
            f"{device_name}"
        )


        return jsonify({

            "success":
                True,

            "message":
                "Device registered successfully"

        })


    except Exception as e:

        log_error(
            "Registration failed: "
            + str(e)
        )


        return jsonify({

            "success":
                False,

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

                "success":
                    False,

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

                "success":
                    False,

                "message":
                    "Missing device name"

            }), 400


        updated = (
            device_manager.heartbeat(

                device_name,

                ip,

                port

            )
        )


        if not updated:

            log(
                f"Heartbeat from unknown "
                f"device -> {device_name}"
            )


            return jsonify({

                "success":
                    False,

                "message":
                    "Device not registered"

            }), 404


        return jsonify({

            "success":
                True,

            "message":
                "Heartbeat received"

        })


    except Exception as e:

        log_error(
            "Heartbeat failed: "
            + str(e)
        )


        return jsonify({

            "success":
                False,

            "message":
                str(e)

        }), 500


@app.route(
    "/devices",
    methods=["GET"]
)
def devices():

    log(
        "Device list requested"
    )


    return jsonify({

        "success":
            True,

        "devices":
            device_manager.get_devices()

    })


@app.route(
    "/probe",
    methods=["POST"]
)
def probe():

    log(
        "Manual device probe requested"
    )


    try:

        data = request.get_json()


        if not data:

            return jsonify({

                "success":
                    False,

                "message":
                    "Missing JSON data"

            }), 400


        ip = data.get(
            "ip"
        )


        if not ip:

            return jsonify({

                "success":
                    False,

                "message":
                    "IP address required"

            }), 400


        port = int(
            data.get(
                "port",
                5001
            )
        )


        url = (
            f"http://{ip}:{port}"
            f"/status"
        )


        log(
            f"Probing laptop -> {url}"
        )


        import requests


        response = requests.get(

            url,

            timeout=5

        )


        if response.status_code != 200:

            return jsonify({

                "success":
                    False,

                "message":
                    "Laptop returned an error"

            }), 400


        laptop = response.json()


        if not laptop.get(
            "success"
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Invalid ScreenLink laptop"

            }), 400


        device_name = laptop.get(
            "device_name"
        )


        if not device_name:

            return jsonify({

                "success":
                    False,

                "message":
                    "Laptop did not provide "
                    "a device name"

            }), 400


        device_manager.add_manual_device(

            device_name,

            ip,

            port

        )


        return jsonify({

            "success":
                True,

            "message":
                "Laptop connected",

            "device": {

                "name":
                    device_name,

                "ip":
                    ip,

                "port":
                    port

            }

        })


    except Exception as e:

        log_error(
            "Probe failed: "
            + str(e)
        )


        return jsonify({

            "success":
                False,

            "message":
                str(e)

        }), 500


@app.route(
    "/screenshot/<device_name>",
    methods=["GET"]
)
def screenshot(device_name):

    log(
        "========================================"
    )


    log(
        "Screenshot request received"
    )


    log(
        f"Device -> {device_name}"
    )


    device = (
        device_manager.get_device(
            device_name
        )
    )


    if not device:

        log(
            "Screenshot failed: "
            "device not found"
        )


        return jsonify({

            "success":
                False,

            "message":
                "Device not found"

        }), 404


    if not device_manager.is_online(
        device
    ):

        log(
            "Screenshot failed: "
            "device is offline"
        )


        return jsonify({

            "success":
                False,

            "message":
                "Device is offline"

        }), 503


    result = screenshot_manager.capture(
        device
    )


    if not result:

        log(
            "Screenshot capture failed"
        )


        return jsonify({

            "success":
                False,

            "message":
                "Screenshot failed"

        }), 500


    return Response(

        result["data"],

        mimetype="image/png"

    )


@app.route(
    "/type/<device_name>",
    methods=["POST"]
)
def type_device(device_name):

    log(
        "========================================"
    )


    log(
        "Typing request received"
    )


    log(
        f"Device -> {device_name}"
    )


    device = device_manager.get_device(
        device_name
    )


    if not device:

        return jsonify({

            "success":
                False,

            "message":
                "Device not found"

        }), 404


    if not device_manager.is_online(
        device
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Device is offline"

        }), 503


    try:

        data = request.get_json()


        if not data:

            return jsonify({

                "success":
                    False,

                "message":
                    "Missing JSON data"

            }), 400


        text = data.get(
            "text"
        )


        if text is None:

            return jsonify({

                "success":
                    False,

                "message":
                    "Missing text"

            }), 400


        import requests


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

            "success":
                False,

            "message":
                str(e)

        }), 500


@app.route(
    "/stop-type/<device_name>",
    methods=["POST"]
)
def stop_type(device_name):

    log(
        "========================================"
    )


    log(
        "Stop typing request received"
    )


    log(
        f"Device -> {device_name}"
    )


    device = device_manager.get_device(
        device_name
    )


    if not device:

        return jsonify({

            "success":
                False,

            "message":
                "Device not found"

        }), 404


    if not device_manager.is_online(
        device
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Device is offline"

        }), 503


    try:

        import requests


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

            "success":
                False,

            "message":
                str(e)

        }), 500


@app.route(
    "/click/<device_name>",
    methods=["POST"]
)
def click_device(device_name):

    log(
        "========================================"
    )


    log(
        "Click execution request received"
    )


    log(
        f"Device -> {device_name}"
    )


    device = device_manager.get_device(
        device_name
    )


    if not device:

        log(
            "Click failed: device not found"
        )


        return jsonify({

            "success":
                False,

            "message":
                "Device not found"

        }), 404


    if not device_manager.is_online(
        device
    ):

        log(
            "Click failed: device offline"
        )


        return jsonify({

            "success":
                False,

            "message":
                "Device is offline"

        }), 503


    try:

        data = request.get_json()


        if not data:

            return jsonify({

                "success":
                    False,

                "message":
                    "Missing JSON data"

            }), 400


        steps = data.get(
            "steps"
        )


        if not isinstance(
            steps,
            list
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "'steps' must be a list"

            }), 400


        if not steps:

            return jsonify({

                "success":
                    False,

                "message":
                    "No click steps provided"

            }), 400


        if len(steps) > 6:

            return jsonify({

                "success":
                    False,

                "message":
                    "Maximum 6 click steps allowed"

            }), 400


        for index, step in enumerate(
            steps,
            start=1
        ):

            if not isinstance(
                step,
                dict
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        f"Invalid step {index}"

                }), 400


            if step.get(
                "action"
            ) != "click":

                return jsonify({

                    "success":
                        False,

                    "message":
                        f"Step {index} must use "
                        f"action 'click'"

                }), 400


            point = step.get(
                "point"
            )


            if not isinstance(
                point,
                dict
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        f"Step {index} is missing "
                        f"point"

                }), 400


            try:

                x = float(
                    point["x"]
                )

                y = float(
                    point["y"]
                )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        f"Step {index} has "
                        f"invalid coordinates"

                }), 400


            if not (
                0 <= x <= 1000
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        f"Step {index} x must "
                        f"be between 0 and 1000"

                }), 400


            if not (
                0 <= y <= 1000
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        f"Step {index} y must "
                        f"be between 0 and 1000"

                }), 400


        import requests


        url = (
            f"http://{device['ip']}:"
            f"{device['port']}"
            f"/click"
        )


        log(
            f"Forwarding click request -> "
            f"{url}"
        )


        log(
            f"Click steps -> {len(steps)}"
        )


        response = requests.post(

            url,

            json={
                "steps": steps
            },

            timeout=30

        )


        log(
            f"Laptop click response -> "
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
            "Click request failed: "
            + str(e)
        )


        return jsonify({

            "success":
                False,

            "message":
                "Unable to execute clicks"

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

    print(
        "       SCREENLINK PHONE SERVER"
    )

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
        "Waiting for laptops..."
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