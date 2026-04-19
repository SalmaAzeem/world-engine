from __future__ import annotations

from gmqtt import Client, Message

from services.command_parser import parse_command_payload
import json
import ssl
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "security_keys.json", "r") as f:
    SECURITY_KEYS = json.load(f)


class MQTTNode:
    def __init__(self, room, config, health_monitor):
        from collections import OrderedDict
        self.room = room
        self.config = config
        self.health_monitor = health_monitor
        self.processed_commands = OrderedDict()
        self.client = Client(
            self._client_id(),
            will_message=Message(
                self.room.status_topic,
                self.room.status_payload("OFFLINE"),
                qos=self.config["mqtt_status_qos"],
                retain=True,
            ),
        )
        self.client.set_config({"reconnect_retries": -1})
        self.client.set_auth_credentials(self.room.room_id, SECURITY_KEYS[self.room.room_id]["password"])
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.ssl_context = ssl.create_default_context(cafile=str(BASE_DIR.parent / "certs" / "server.crt"))
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE


    def _client_id(self):
        return f"{self.config['mqtt_client_prefix']}-{self.room.room_id}"

    async def start(self):
        import asyncio
        while True:
            try:
                await self.client.connect(
                    self.config["mqtt_broker"],
                    port=self.config.get("mqtt_tls_port", 8883),
                    keepalive=self.config["mqtt_keepalive"],
                    ssl=self.ssl_context
                )
                break
            except Exception as e:
                print(f"[MQTT WAIT] Node {self.room.room_id} waiting for broker: {e}")
                await asyncio.sleep(3)

    async def stop(self):
        if not self.client.is_connected:
            return

        self.client.publish(
            self.room.status_topic,
            self.room.status_payload("OFFLINE"),
            qos=self.config["mqtt_status_qos"],
            retain=True,
        )
        await self.client.disconnect()

    async def publish_telemetry(self, payload):
        if not self.client.is_connected:
            return

        self.client.publish(
            self.room.telemetry_topic,
            payload,
            qos=self.config["mqtt_telemetry_qos"],
        )

    def _on_connect(self, client, flags, rc, properties):
        self.health_monitor.record_heartbeat(self.room.room_id, self.room.protocol)
        self.health_monitor.set_status(self.room.room_id, "ONLINE")
        
        command_qos = self.config.get("mqtt_command_qos", 2)
        if command_qos < 2:
            print(f"[SECURITY WARNING] {self.room.room_id} subscribing to commands below QoS 2. Emergency Lockout risks race conditions!")
            
        client.subscribe(self.room.command_topic, qos=command_qos)
        client.publish(
            self.room.status_topic,
            self.room.status_payload("ONLINE"),
            qos=self.config["mqtt_status_qos"],
            retain=True,
        )
        print(f"[MQTT] {self.room.room_id} connected")

    def _on_disconnect(self, client, packet, exc=None):
        self.health_monitor.set_status(self.room.room_id, "OFFLINE")
        if exc:
            print(f"[MQTT] {self.room.room_id} disconnected with error: {exc}")
        else:
            print(f"[MQTT] {self.room.room_id} disconnected")

    def _on_message(self, client, topic, payload, qos, properties):
        command = parse_command_payload(payload)
        if command is None:
            print(f"[MQTT] Ignored malformed command for {self.room.room_id}")
            return

        # DUP flag & idempotency handler
        message_id = command.get("message_id")
        if message_id:
            if message_id in self.processed_commands:
                print(f"[MQTT DUP CAUGHT] Dropping duplicate command {message_id} on {self.room.room_id}")
                return
            self.processed_commands[message_id] = True
            if len(self.processed_commands) > 100:
                self.processed_commands.popitem(last=False)

        self.room.apply_command(command)
        self.health_monitor.record_heartbeat(self.room.room_id, self.room.protocol)
        self.client.publish(
            self.room.telemetry_topic,
            self.room.telemetry_payload(),
            qos=self.config["mqtt_telemetry_qos"],
        )
        self.client.publish(
            self.room.response_topic,
            self.room.command_response("mqtt"),
            qos=self.config["mqtt_status_qos"],
        )
        print(f"[MQTT] Applied command to {self.room.room_id} from topic {topic}")
