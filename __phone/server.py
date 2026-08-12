from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    Response
)

import os
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


# =========================================
# PATHS
# =========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROMPT_DIRECTORY = os.path.join(
    BASE_DIR,
    "prompts"
)


PROMPT_FILES = {

    "click": "click.txt",

    "python": "python.txt",

    "sql": "sql.txt",

    "fill_blank": "fill_blank.txt",

    "email": "email.txt",

    "general": "general.txt",

    "custom": "custom.txt"

}


# =========================================
# CONFIG
# =========================================

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


# =========================================
# MANAGERS
# =========================================

device_manager = DeviceManager(
    HEARTBEAT_TIMEOUT
)


screenshot_manager = ScreenshotManager(
    SCREENSHOT_DIRECTORY
)


# =========================================
# WEB PAGE
# =========================================

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


# =========================================
# PHONE STATUS
# =========================================

@app.route(
    "/status",
    methods=["GET"]
)
def status():

    return jsonify({

        "success": True,

        "service":
            "ScreenLink",

        "status":
            "online",

        "ip":
            get_phone_ip(),

        "port":
            PORT

    })


# =========================================
# PROMPTS
# =========================================

@app.route(
    "/prompts/<prompt_name>",
    methods=["GET"]
)
def get_prompt(prompt_name):

    filename = PROMPT_FILES.get(
        prompt_name
    )

    if not filename:

        return jsonify({

            "success":
                False,

            "message":
                "Prompt not found"

        }), 404


    path = os.path.join(
        PROMPT_DIRECTORY,
        filename
    )


    if not os.path.isfile(path):

        log_error(
            f"Prompt file missing -> {path}"
        )

        return jsonify({

            "success":
                False,

            "message":
                "Prompt file is missing"

        }), 404


    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()


        return Response(

            content,

            mimetype="text/plain",

            headers={

                "Cache-Control":
                    "no-store"

            }

        )


    except Exception as e:

        log_error(
            "Failed to load prompt: "
            + str(e)
        )

        return jsonify({

            "success":
                False,

            "message":
                "Unable to load prompt"

        }), 500


# =========================================
# REGISTER
# =========================================

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


# =========================================
# HEARTBEAT
# =========================================

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


        updated = device_manager.heartbeat(

            device_name,

            ip,

            port

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


# =========================================
# DEVICES
# =========================================

@app.route(
    "/devices",
    methods=["GET"]
)
def devices():

    return jsonify({

        "success":
            True,

        "devices":
            device_manager.get_devices()

    })


# =========================================
# MANUAL PROBE
# =========================================

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


        import requests


        log(
            f"Probing laptop -> {url}"
        )


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


# =========================================
# SCREENSHOT
# =========================================

@app.route(
    "/screenshot/<device_name>",
    methods=["GET"]
)
def screenshot(device_name):

    log(
        "Screenshot request received"
    )

    log(
        f"Device -> {device_name}"
    )


    device = device_manager.get_device(
        device_name
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

        return jsonify({

            "success":
                False,

            "message":
                "Screenshot failed"

        }), 500


    return Response(

        result["data"],

        mimetype="image/png",

        headers={

            "Cache-Control":
                "no-store",

            "X-ScreenLink-Timestamp":
                result["timestamp"],

            "X-ScreenLink-Filename":
                result["filename"]

        }

    )


# =========================================
# CLICK
# =========================================

@app.route(
    "/click/<device_name>",
    methods=["POST"]
)
def click_device(device_name):

    log(
        "Click request received"
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
                    "Steps must be a list"

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
                    "Maximum 6 clicks allowed"

            }), 400


        for step in steps:

            if not isinstance(
                step,
                dict
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Invalid click step"

                }), 400


            if step.get(
                "action"
            ) != "click":

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Invalid click action"

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
                        "Missing click point"

                }), 400


            x = point.get(
                "x"
            )


            y = point.get(
                "y"
            )


            if not isinstance(
                x,
                (int, float)
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Invalid x coordinate"

                }), 400


            if not isinstance(
                y,
                (int, float)
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Invalid y coordinate"

                }), 400


            if (
                x < 0
                or x > 1000
                or y < 0
                or y > 1000
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Coordinates must be between 0 and 1000"

                }), 400


        import requests


        url = (
            f"http://{device['ip']}:"
            f"{device['port']}"
            f"/click"
        )


        log(
            "Sending click request to laptop"
        )


        response = requests.post(

            url,

            json=data,

            timeout=10

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
                str(e)

        }), 500


# =========================================
# TYPE
# =========================================

@app.route(
    "/type/<device_name>",
    methods=["POST"]
)
def type_device(device_name):

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


        response = requests.post(

            url,

            json={
                "text": text
            },

            timeout=5

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


# =========================================
# STOP TYPING
# =========================================

@app.route(
    "/stop-type/<device_name>",
    methods=["POST"]
)
def stop_type_device(device_name):

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


        response = requests.post(

            url,

            timeout=5

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
            "Stop typing failed: "
            + str(e)
        )

        return jsonify({

            "success":
                False,

            "message":
                str(e)

        }), 500


# =========================================
# SHUTDOWN
# =========================================

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


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        shutdown
    )


    signal.signal(
        signal.SIGTERM,
        shutdown
    )


    os.makedirs(
        PROMPT_DIRECTORY,
        exist_ok=True
    )


    phone_ip = get_phone_ip()


    print()

    print(
        f"Phone IP       : {phone_ip}"
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
        f"Prompt directory -> "
        f"{PROMPT_DIRECTORY}"
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