#!/usr/bin/env python3

import sys
import argparse
import threading
import time
import json
import os
import socket
import tinytuya
from flask import Flask, jsonify, request
from werkzeug.serving import make_server

app = Flask(__name__)

# Global state for devices: dev_id -> {name, version, ip}
devices = {}
scan_lock = threading.Lock()  # Lock for scan to ensure only one scan at a time
scanning = False  # Track if a scan is in progress
devices_file = None  # Will be set from args

def load_devices():
    global devices
    with open(devices_file) as f:
        devices = json.load(f)

def get_device_instance(dev_id, ip=None):
    # Reload devices every request
    load_devices()
    dev_info = devices.get(dev_id)
    if not dev_info:
        raise KeyError(f"Device ID {dev_id} not found")
    # IP comes from the scan or user updates
    ip = ip or dev_info.get("ip")
    if not ip:
        raise RuntimeError(f"No IP for device {dev_id}")
    version = dev_info.get("version", "3.4")
    return tinytuya.OutletDevice(dev_id, ip, dev_info["local_key"], version=version)

def scan_devices():
    global scanning
    if scanning:
        return False
    scanning = True

    try:
        results = tinytuya.deviceScan(False, 10)  # Scan 10 sec
        load_devices()  # Refresh devices from file
        for dev in results.values():
            dev_id = dev["id"]
            if dev_id in devices:
                devices[dev_id]["ip"] = dev["ip"]
        # Return the devices with updated IPs
        return {dev_id: devices[dev_id] for dev_id in results}
    finally:
        scanning = False

def scan_devices_periodically():
    while True:
        if not scanning:
            scan_devices()
        time.sleep(300)

@app.before_request
def startup():
    # Start scanning thread once on first request
    threading.Thread(target=scan_devices_periodically, daemon=True).start()

@app.route("/scan", methods=["POST"])
def manual_scan():
    if scan_lock.locked():
        return jsonify({"error": "Scan in progress"}), 400

    with scan_lock:
        result = scan_devices()
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Scan failed or in progress"}), 500

@app.route("/<dev_id>/state", methods=["GET"])
def get_state(dev_id):
    try:
        d = get_device_instance(dev_id)
        return jsonify(d.status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/<dev_id>/on", methods=["GET"])
def is_on(dev_id):
    try:
        d = get_device_instance(dev_id)
        status = d.status()
        on_state = status.get("dps", {}).get("1")
        return jsonify({"on": bool(on_state)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/<dev_id>/on", methods=["POST"])
def turn_on(dev_id):
    try:
        d = get_device_instance(dev_id)
        d.turn_on()
        return jsonify({"result": "Device turned ON"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/<dev_id>/off", methods=["POST"])
def turn_off(dev_id):
    try:
        d = get_device_instance(dev_id)
        d.turn_off()
        return jsonify({"result": "Device turned OFF"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/<dev_id>/toggle", methods=["POST"])
def toggle(dev_id):
    try:
        d = get_device_instance(dev_id)
        status = d.status()
        current = status.get("dps", {}).get("1")
        if current:
            d.turn_off()
            return jsonify({"result": "Device toggled OFF"})
        else:
            d.turn_on()
            return jsonify({"result": "Device toggled ON"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    global devices_file

    parser = argparse.ArgumentParser(
        description="""\
tiny-tuya-rest server. Locally forward requests to a local server.
Settings are read from a `tuya-devices.json` file mapping device IDs to info dicts.

See README https://github.com/talwrii/tuya-tiny-web for details on obtaining local_key.
""",
        epilog="@readwithai 📖 https://readwithai.substack.com/p/habits ⚡️ machine-aided reading ✒️"
    )

    # Mutually exclusive group for unix socket vs host (port is ignored if unix-socket)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--unix-socket", help="Unix domain socket path to bind the REST server")
    group.add_argument("--host", default="0.0.0.0", help="IP to bind the REST server")

    parser.add_argument("--port", type=int, default=1024, help="Port for REST server (ignored with --unix-socket)")
    parser.add_argument("--devices-file", default="tuya-devices.json", help="JSON file with device info")

    args = parser.parse_args()
    devices_file = args.devices_file

    # Safety check - don't allow mixing unix socket and host/port
    if args.unix_socket and ('--port' in sys.argv or '--host' in sys.argv):
        raise Exception('Either use --unix-socket or --host and --port, not both')

    load_devices()

    if args.unix_socket:
        app.run(host='unix://' + args.unix_socket)
    else:
        app.run(host=args.host, port=args.port)

    print(f"Serving on {'unix socket ' + args.unix_socket if args.unix_socket else f'{args.host}:{args.port}'}")

if __name__ == "__main__":
    main()
