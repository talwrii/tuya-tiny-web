#!/usr/bin/env python3

import sys
import argparse
import threading
import time
import json
import os
import socket
import tinytuya
import functools
from flask import Flask, jsonify, request
from werkzeug.serving import make_server

app = Flask(__name__)

# Global state for devices: dev_id -> {name, version, ip}
devices = {}
device_ips = {}  # dev_id -> ip
scan_lock = threading.Lock()  # Lock for scan to ensure only one scan at a time
scanning = False  # Track if a scan is in progress
devices_file = None  # Will be set from args

def load_devices():
    global devices
    with open(devices_file) as f:
        devices = json.load(f)

def resolve_device_id(identifier):
    """Allow using either dev_id or friendly name."""
    load_devices()
    if identifier in devices:
        return identifier
    for dev_id, info in devices.items():
        if info.get("name") == identifier:
            return dev_id
    raise KeyError(f"No device found with id or name: {identifier}")

def get_device_instance(identifier):
    dev_id = resolve_device_id(identifier)
    info = devices[dev_id]
    return tinytuya.OutletDevice(dev_id, device_ips[dev_id], info["local_key"], version=info["version"])

def scan_devices():
    global scanning
    if scanning:
        return False
    scanning = True

    try:
        print("Scanning for devices...")
        results = tinytuya.deviceScan(False, 10)  # Scan 10 sec
        load_devices()  # Refresh devices from file

        for info in results.values():
            if info["ip"] != device_ips.get(info["id"]):
                print(f"New ip for device: {info['id']} -> {info['ip']}")
                device_ips[info["id"]] = info["ip"]
        print("Done scanning")
    finally:
        scanning = False


def scan_devices_periodically():
    try:
        while True:
            if not scanning:
                scan_devices()
            time.sleep(300)
    except Exception:
        print('Failed to scan exits', stream=sys.stderr)
        os._exit(1)


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

def with_errors(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": type(e).__name__, "message": str(e)}), 500
    return inner

@app.route("/<dev_id>/state", methods=["GET"])
@with_errors
def get_state(dev_id):
    d = get_device_instance(dev_id)
    return jsonify(d.status())

@app.route("/<dev_id>/on", methods=["GET"])
@with_errors
def is_on(dev_id):
    d = get_device_instance(dev_id)
    status = d.status()
    on_state = status.get("dps", {}).get("1")
    return jsonify({"on": bool(on_state)})

@app.route("/<dev_id>/on", methods=["POST"])
@with_errors
def turn_on(dev_id):
    d = get_device_instance(dev_id)
    d.turn_on()
    return jsonify({"result": "Device turned ON"})

@app.route("/<dev_id>/off", methods=["POST"])
@with_errors
def turn_off(dev_id):
    d = get_device_instance(dev_id)
    d.turn_off()
    return jsonify({"result": "Device turned OFF"})

@app.route("/<dev_id>/toggle", methods=["POST"])
@with_errors
def toggle(dev_id):
    d = get_device_instance(dev_id)
    status = d.status()
    current = status.get("dps", {}).get("1")
    if current:
        d.turn_off()
        return jsonify({"result": "Device toggled OFF"})
    else:
        d.turn_on()
        return jsonify({"result": "Device toggled ON"})


def main():
    global devices_file

    parser = argparse.ArgumentParser(
        description="""\
tiny-tuya-rest server. Locally forward requests to a local server.
Settings are read from a `tuya-devices.json` file mapping device IDs to info dicts.

See README https://github.com/talwrii/tuya-tiny-web for details on obtaining local_key.
""",
        epilog="@readwithai 📖 https://readwithai.substack.com/p/habits ⚡ machine-aided reading ✒"
    )

    # Mutually exclusive group for unix socket vs host (port is ignored if unix-socket)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--unix-socket", help="Unix domain socket path to bind the REST server")
    group.add_argument("--host", default="0.0.0.0", help="IP to bind the REST server")

    parser.add_argument("--port", type=int, default=1024, help="Port for REST server")
    parser.add_argument("--devices-file", default="tuya-devices.json", help="JSON file with device info")

    args = parser.parse_args()
    devices_file = args.devices_file

    threading.Thread(target=scan_devices_periodically, daemon=True).start()


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
