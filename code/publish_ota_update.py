from __future__ import annotations

import argparse
import json
import ssl
import time
from pathlib import Path

import paho.mqtt.client as mqtt

from services.security_utils import calculate_fingerprint


BASE_DIR = Path(__file__).resolve().parent


def load_subscriber_password():
    with open(BASE_DIR / "security_keys.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)["subscriber"]["password"]


def build_payload(version, alpha, beta):
    payload = {
        "version": version,
        "params": {},
    }
    if alpha is not None:
        payload["params"]["alpha"] = alpha
    if beta is not None:
        payload["params"]["beta"] = beta

    payload["signature"] = calculate_fingerprint(payload)
    return payload


def parse_args():
    parser = argparse.ArgumentParser(description="Publish a signed OTA config update to HiveMQ.")
    parser.add_argument("--topic", required=True, help="OTA topic, e.g. campus/b01/f05/ota/config")
    parser.add_argument("--version", required=True, help="New fleet config/firmware version, e.g. 1.1")
    parser.add_argument("--alpha", type=float, help="Optional thermal leakage constant")
    parser.add_argument("--beta", type=float, help="Optional heat capacity/HVAC constant")
    parser.add_argument("--host", default="localhost", help="MQTT host exposed by Docker")
    parser.add_argument("--port", type=int, default=8883, help="MQTT port exposed by Docker")
    parser.add_argument("--username", default="subscriber", help="HiveMQ username")
    parser.add_argument("--password", default=None, help="HiveMQ password; defaults to security_keys.json subscriber password")
    parser.add_argument("--no-tls", action="store_true", help="Use plain MQTT instead of TLS")
    parser.add_argument("--tamper", action="store_true", help="Modify the payload after signing to demo rejection")
    return parser.parse_args()


def main():
    args = parse_args()
    payload = build_payload(args.version, args.alpha, args.beta)
    if args.tamper:
        payload["params"]["alpha"] = 9.99

    client = mqtt.Client(client_id=f"ota-publisher-{int(time.time())}")
    client.username_pw_set(args.username, args.password or load_subscriber_password())

    if not args.no_tls:
        client.tls_set(
            ca_certs=str(BASE_DIR.parent / "certs" / "server.crt"),
            cert_reqs=ssl.CERT_NONE,
        )
        client.tls_insecure_set(True)

    client.connect(args.host, args.port, 60)
    result = client.publish(args.topic, json.dumps(payload, sort_keys=True), qos=1)
    result.wait_for_publish()
    client.disconnect()

    print(f"Published signed OTA update to {args.topic}")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
