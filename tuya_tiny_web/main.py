#!/usr/bin/env python3

import argparse
import threading
import time
import json
import tinytuya
from flask import Flask, jsonify, request

app = Flask(__name__)

# Global state for devices: dev_id -> {name, version, ip}
devices = {}
scan_lock = threading.Lock()  # Lock for scan to ensure only one scan at a time
scanning = False  # Track if a scan is in progress

def load_devices(filename="tuya_devices.json"):
    global devices
    with open(filename) as f:
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
        return False  # Don't start a scan if one is already running
    scanning = True

    try:
        results = tinytuya.deviceScan(False, 10)  # Scan for 10 seconds
        # Update devices with IPs from scan results
        with open("tuya_devices.json", "r+") as f:
            data = json.load(f)
            for dev in results.values():
                dev_id = dev["id"]
                if dev_id in data:
                    data[dev_id]["ip"] = dev["ip"]
            f.seek(0)
            json.dump(data, f, indent=4)
        # Return the devices with updated IPs
        return {dev_id: devices[dev_id] for dev_id in results}
    finally:
        scanning = False  # Reset scanning flag after the scan

def scan_devices_periodically():
    while True:
        if not scanning:  # Avoid running scan if it's already in progress
            scan_devices()
        time.sleep(300)  # scan every 5 mins

@app.before_first_request
def startup():
    # Start device scan thread
    threading.Thread(target=scan_devices_periodically, daemon=True).start()

@app.route("/scan", methods=["POST"])
def manual_scan():
    if scan_lock.locked():
        return jsonify({"error": "Scan is already in progress. Try again later."}), 400

    with scan_lock:
        scan_result = scan_devices()  # Trigger manual scan
        if scan_result:
            return jsonify(scan_result)  # Return the devices with updated IPs
        else:
            return jsonify({"error": "Scan already in progress or failed"}), 500

@app.route("/<dev_id>/state", methods=["GET"])
def get_state(dev_id):
    try:
        d = get_device_instance(dev_id)
        status = d.status()
        return jsonify(status)
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
    parser = argparse.ArgumentParser(description="tiny-tuya-rest server")
    parser.add_argument("--host", default="0.0.0.0", help="IP to bind the REST server")
    parser.add_argument("--port", type=int, default=1024, help="Port for REST server")
    parser.add_argument("--devices-file", default="tuya_devices.json", help="JSON file with device info")
    args = parser.parse_args()

    load_devices(args.devices_file)

    app.run(host=args.host, port=args.port, threaded=True)

if __name__ == "__main__":
    main()
