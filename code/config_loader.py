from __future__ import annotations

import os
from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parent


ENV_MAPPING = {
    "BUILDING_ID": ("building_id", str),
    "FLOORS": ("floors", int),
    "ROOMS_PER_FLOOR": ("rooms_per_floor", int),
    "MQTT_ROOMS_PER_FLOOR": ("mqtt_rooms_per_floor", int),
    "COAP_ROOMS_PER_FLOOR": ("coap_rooms_per_floor", int),
    "MQTT_BROKER": ("mqtt_broker", str),
    "MQTT_PORT": ("mqtt_port", int),
    "MQTT_KEEPALIVE": ("mqtt_keepalive", int),
    "MQTT_CLIENT_PREFIX": ("mqtt_client_prefix", str),
    "MQTT_TELEMETRY_QOS": ("mqtt_telemetry_qos", int),
    "MQTT_STATUS_QOS": ("mqtt_status_qos", int),
    "MQTT_COMMAND_QOS": ("mqtt_command_qos", int),
    "COAP_BIND_HOST": ("coap_bind_host", str),
    "COAP_PUBLIC_HOST": ("coap_public_host", str),
    "COAP_BASE_PORT": ("coap_base_port", int),
    "OUTSIDE_TEMP_DAY": ("outside_temp_day", float),
    "OUTSIDE_TEMP_NIGHT": ("outside_temp_night", float),
    "ALPHA": ("alpha", float),
    "BETA": ("beta", float),
    "OCCUPANCY_HEAT": ("occupancy_heat", float),
    "OCCUPIED_LIGHT_THRESHOLD": ("occupied_light_threshold", int),
    "TICK_INTERVAL": ("tick_interval", float),
    "MAX_JITTER": ("max_jitter", float),
    "TIME_ACCELERATION": ("time_acceleration", float),
    "HEARTBEAT_TIMEOUT": ("heartbeat_timeout", int),
    "HEALTH_CHECK_INTERVAL": ("health_check_interval", int),
    "DB_SYNC_INTERVAL": ("db_sync_interval", int),
}


def load_config(config_path=None):
    config_path = Path(config_path or os.getenv("CONFIG_PATH", BASE_DIR / "config.yaml"))

    with open(config_path, "r", encoding="utf-8") as file_handle:
        config = yaml.safe_load(file_handle)

    for env_name, (config_key, cast) in ENV_MAPPING.items():
        raw_value = os.getenv(env_name)
        if raw_value is None:
            continue
        config[config_key] = cast(raw_value)

    if "COAP_SERVER_TRANSPORTS" in os.environ:
        config["coap_server_transports"] = [
            item.strip()
            for item in os.environ["COAP_SERVER_TRANSPORTS"].split(",")
            if item.strip()
        ]

    return config
