import socket
import threading
import time
import sys

import requests

from flask import Flask, jsonify, send_file

from config import load_config, save_config
from logger import log, log_error, get_log_file
from typer import type_text
from network import get_local_ip
from screenshot import capture_screen


app = Flask(__name__)

config = load_config()

PHONE_IP = config["phone_ip"]
PHONE_PORT = int(config["phone_port"])

LAPTOP_PORT = int(
    config["laptop_port"]
)

HEARTBEAT_INTERVAL = int(
    config["heartbeat_interval"]
)

RETRY_INTERVAL = int(
    config["connection_retry_interval"]
)

DEVICE_NAME = socket.gethostname()

running = True
registered = False


def phone_base_url():

    return (
        f"http://{PHONE_IP}:"
        f"{PHONE_PORT}"
    )


def check_phone():

    url = (
        f"{phone_base_url()}"
        f"/status"
    )

    log(
        f"Checking ScreenLink phone -> {url}"
    )

    try:

        response = requests.get(
            url,
            timeout=5
        )

        if response.status_code == 200:

            data = response.json()

            if data.get("success"):

                log(
                    "ScreenLink phone server found"
                )

                return True

        log(
            "Phone responded, but is not "
            "a valid ScreenLink server"
        )

        return False

    except Exception as e:

        log(
            "Phone unavailable -> "
            + str(e)
        )

        return False


def ask_for_phone_ip():

    global PHONE_IP

    print()

    if PHONE_IP:

        print(
            f"Last used phone IP: "
            f"{PHONE_IP}"
        )

        answer = input(
            "Use this IP? [Y/n]: "
        ).strip().lower()

        if answer in ("", "y", "yes"):

            return

    while True:

        ip = input(
            "Enter the IP address of the phone: "
        ).strip()

        if not ip:

            print(
                "IP address cannot be empty."
            )

            continue

        PHONE_IP = ip

        config["phone_ip"] = PHONE_IP

        save_config(config)

        print(
            f"Phone IP saved -> {PHONE_IP}"
        )

        return


def register():

    global registered

    laptop_ip = get_local_ip()

    url = (
        f"{phone_base_url()}"
        f"/register"
    )

    data = {
        "device_name": DEVICE_NAME,
        "ip": laptop_ip,
        "port": LAPTOP_PORT
    }

    log(
        "Registration attempt"
    )

    log(
        f"Phone -> {url}"
    )

    log(
        f"Device -> {DEVICE_NAME}"
    )

    log(
        f"Laptop IP -> {laptop_ip}"
    )

    log(
        f"Laptop port -> {LAPTOP_PORT}"
    )

    try:

        response = requests.post(
            url,
            json=data,
            timeout=5
        )

        log(
            f"Registration response -> "
            f"{response.status_code}"
        )

        if response.status_code == 200:

            registered = True

            log(
                "Registration successful"
            )

            return True

        registered = False

        log(
            "Registration rejected"
        )

        return False

    except Exception as e:

        registered = False

        log_error(
            "Registration failed: "
            + str(e)
        )

        return False


def heartbeat():

    global registered

    laptop_ip = get_local_ip()

    url = (
        f"{phone_base_url()}"
        f"/heartbeat"
    )

    data = {
        "device_name": DEVICE_NAME,
        "ip": laptop_ip,
        "port": LAPTOP_PORT
    }

    try:

        response = requests.post(
            url,
            json=data,
            timeout=5
        )

        if response.status_code == 200:

            if not registered:

                log(
                    "Heartbeat successful"
                )

            registered = True

            return True

        if response.status_code == 404:

            registered = False

            log(
                "Laptop is not registered "
                "with phone"
            )

            return False

        registered = False

        log(
            f"Heartbeat failed -> "
            f"{response.status_code}"
        )

        return False

    except Exception as e:

        registered = False

        log(
            "Phone unavailable during "
            "heartbeat -> "
            + str(e)
        )

        return False


def heartbeat_loop():

    global running
    global registered

    while running:

        time.sleep(
            HEARTBEAT_INTERVAL
        )

        if not running:
            break

        if registered:

            success = heartbeat()

            if not success:

                log(
                    "Heartbeat lost. "
                    "Waiting for phone..."
                )

        else:

            log(
                "Attempting to reconnect "
                "to phone..."
            )

            if check_phone():

                if register():

                    log(
                        "Re-registration successful"
                    )


@app.route(
    "/status",
    methods=["GET"]
)
def status():

    log(
        "Status request received"
    )

    return jsonify({

        "success": True,

        "device_name": DEVICE_NAME,

        "ip": get_local_ip(),

        "port": LAPTOP_PORT,

        "status": "online"

    })
    
@app.route(
    "/type",
    methods=["POST"]
)
def type_endpoint():

    log(
        "========================================"
    )

    log(
        "Typing request received"
    )

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message":
                    "Missing JSON data"
            }), 400

        text = data.get("text")

        if text is None:

            return jsonify({
                "success": False,
                "message":
                    "Missing text"
            }), 400

        if not text:

            return jsonify({
                "success": False,
                "message":
                    "Text cannot be empty"
            }), 400

        log(
            f"Text length -> {len(text)}"
        )

        threading.Thread(
            target=type_text,
            args=(text,),
            daemon=True
        ).start()

        log(
            "Typing started"
        )

        return jsonify({

            "success": True,

            "message":
                "Typing started"

        })

    except Exception as e:

        log_error(
            "Typing request failed: "
            + str(e)
        )

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


@app.route(
    "/screenshot",
    methods=["GET"]
)
def screenshot():

    request_time = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    log(
        "========================================"
    )

    log(
        "Screenshot request received"
    )

    log(
        f"Request time -> {request_time}"
    )

    result = capture_screen()

    if not result:

        log(
            "Screenshot request failed"
        )

        return jsonify({

            "success": False,

            "message":
                "Screenshot capture failed"

        }), 500

    try:

        log(
            "Sending screenshot to phone"
        )

        response = send_file(

            result["path"],

            mimetype="image/png",

            as_attachment=False,

            download_name=result["filename"]
        )

        response.headers[
            "X-ScreenLink-Timestamp"
        ] = result["timestamp"]

        response.headers[
            "X-ScreenLink-Filename"
        ] = result["filename"]

        return response

    except Exception as e:

        log_error(
            "Failed to send screenshot: "
            + str(e)
        )

        return jsonify({

            "success": False,

            "message":
                "Failed to send screenshot"

        }), 500


def start_server():

    log(
        f"Starting laptop HTTP server "
        f"on port {LAPTOP_PORT}"
    )

    app.run(

        host="0.0.0.0",

        port=LAPTOP_PORT,

        debug=False,

        use_reloader=False

    )


def shutdown():

    global running

    running = False

    log(
        "ScreenLink laptop shutting down"
    )


def main():

    global PHONE_IP

    print()
    print("=" * 45)
    print("       SCREENLINK LAPTOP")
    print("=" * 45)

    print(
        f"Device         : {DEVICE_NAME}"
    )

    print(
        f"Laptop IP      : {get_local_ip()}"
    )

    print(
        f"Laptop Port    : {LAPTOP_PORT}"
    )

    print()

    ask_for_phone_ip()

    print(
        f"Phone IP       : {PHONE_IP}"
    )

    print(
        f"Phone Port     : {PHONE_PORT}"
    )

    print()

    log(
        "========================================"
    )

    log(
        "ScreenLink laptop starting"
    )

    log(
        f"Device -> {DEVICE_NAME}"
    )

    log(
        f"Laptop IP -> {get_local_ip()}"
    )

    log(
        f"Laptop port -> {LAPTOP_PORT}"
    )

    log(
        f"Phone IP -> {PHONE_IP}"
    )

    log(
        f"Phone port -> {PHONE_PORT}"
    )

    log(
        f"Log file -> {get_log_file()}"
    )

    print()

    while True:

        print(
            "Checking ScreenLink phone..."
        )

        if check_phone():

            print(
                "Phone found."
            )

            break

        print(
            f"Phone unavailable. "
            f"Retrying in {RETRY_INTERVAL} seconds..."
        )

        time.sleep(
            RETRY_INTERVAL
        )

    while not register():

        print(
            f"Registration failed. "
            f"Retrying in {RETRY_INTERVAL} seconds..."
        )

        time.sleep(
            RETRY_INTERVAL
        )

    heartbeat_thread = threading.Thread(

        target=heartbeat_loop,

        daemon=True

    )

    heartbeat_thread.start()

    print()
    print("=" * 45)
    print("Registration successful.")
    print("Status         : ONLINE")
    print("=" * 45)
    print()

    try:

        start_server()

    except KeyboardInterrupt:

        print()
        print(
            "Stopping ScreenLink..."
        )

        shutdown()

    except Exception as e:

        log_error(
            "Server crashed: "
            + str(e)
        )

        shutdown()


if __name__ == "__main__":

    main()