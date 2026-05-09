from __future__ import annotations

import asyncio
import json
import ssl
from pathlib import Path

from gmqtt import Client

from services.ota_update import OTA_TOPIC_FILTERS, apply_ota_update, matching_rooms
from services.security_utils import verify_fingerprint


BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "security_keys.json", "r") as f:
    SECURITY_KEYS = json.load(f)


class FleetOTAClient:
    def __init__(self, rooms, config, health_monitor):
        self.rooms = list(rooms)
        self.config = config
        self.health_monitor = health_monitor
        self.client = Client("fleet-ota-subscriber")
        self.client.set_config({"reconnect_retries": -1})
        self.client.set_auth_credentials("subscriber", SECURITY_KEYS["subscriber"]["password"])
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.ssl_context = ssl.create_default_context(cafile=str(BASE_DIR.parent / "certs" / "server.crt"))
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def start(self):
        while True:
            try:
                await self.client.connect(
                    self.config["mqtt_broker"],
                    port=self.config.get("mqtt_tls_port", 8883),
                    keepalive=self.config["mqtt_keepalive"],
                    ssl=self.ssl_context,
                )
                break
            except OSError as exc:
                print(f"[OTA] Connection to broker failed: {exc}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def stop(self):
        if self.client.is_connected:
            await self.client.disconnect()

    def _on_connect(self, client, flags, rc, properties):
        qos = self.config.get("mqtt_command_qos", 2)
        for topic_filter in OTA_TOPIC_FILTERS:
            client.subscribe(topic_filter, qos=qos)
        print(f"[OTA] Fleet OTA subscriber connected to {len(OTA_TOPIC_FILTERS)} topic filters")

    def _on_disconnect(self, client, packet, exc=None):
        if exc:
            print(f"[OTA] Fleet OTA subscriber disconnected with error: {exc}")
        else:
            print("[OTA] Fleet OTA subscriber disconnected")

    def _on_message(self, client, topic, payload, qos, properties):
        target_rooms = matching_rooms(topic, self.rooms)
        if not target_rooms:
            print(f"[OTA] Ignored OTA message for unmatched topic {topic}")
            return

        try:
            raw_data = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
        except Exception:
            print(f"[OTA] Failed to decode OTA payload from {topic}")
            self._publish_tamper_alert(target_rooms, "Malformed OTA JSON payload")
            return

        if not verify_fingerprint(raw_data):
            print(f"[SECURITY TAMPERING ALERT] Invalid OTA hash detected from {topic}")
            self._publish_tamper_alert(target_rooms, "OTA SHA-256 Signature Mismatch or Missing")
            return

        try:
            applied_count = 0
            for room in target_rooms:
                update = apply_ota_update(room, raw_data)
                self.health_monitor.record_heartbeat(room.room_id, room.protocol)
                self.client.publish(
                    room.telemetry_topic,
                    json.dumps(room.telemetry_payload()),
                    qos=self.config["mqtt_telemetry_qos"],
                )
                applied_count += 1
            print(
                f"[OTA] Applied version={update.version} params={update.params} "
                f"to {applied_count} room(s) from {topic}"
            )
        except ValueError as exc:
            print(f"[OTA] Rejected OTA payload from {topic}: {exc}")
            self._publish_tamper_alert(target_rooms, f"Malformed OTA config payload: {exc}")

    def _publish_tamper_alert(self, rooms, details):
        for room in rooms:
            alert_payload = room.tampering_alert_payload(details)
            self.client.publish(
                room.telemetry_topic,
                json.dumps(alert_payload),
                qos=self.config["mqtt_telemetry_qos"],
            )
