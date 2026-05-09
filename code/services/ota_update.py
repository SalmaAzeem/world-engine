from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


OTA_TOPIC_FILTERS = (
    "campus/+/ota/config",
    "campus/+/+/ota/config",
    "campus/+/+/+/ota/config",
)
ALLOWED_OTA_PARAMS = {"alpha", "beta"}


@dataclass(frozen=True)
class OTATarget:
    building: str
    floor: str | None = None
    room: str | None = None


@dataclass(frozen=True)
class OTAUpdate:
    version: str | None
    params: dict[str, float]


def parse_ota_topic(topic: str) -> OTATarget | None:
    parts = topic.split("/")

    if len(parts) == 4 and parts[0] == "campus" and parts[2:] == ["ota", "config"]:
        return OTATarget(building=parts[1])

    if len(parts) == 5 and parts[0] == "campus" and parts[3:] == ["ota", "config"]:
        return OTATarget(building=parts[1], floor=parts[2])

    if len(parts) == 6 and parts[0] == "campus" and parts[4:] == ["ota", "config"]:
        return OTATarget(building=parts[1], floor=parts[2], room=parts[3])

    return None


def ota_topic_matches_room(topic: str, room) -> bool:
    target = parse_ota_topic(topic)
    if target is None:
        return False

    if target.building != f"b{room.building_id}":
        return False

    if target.floor is not None and target.floor != f"f{room.floor_id:02d}":
        return False

    if target.room is not None and target.room != f"r{room.room_number}":
        return False

    return True


def matching_rooms(topic: str, rooms: Iterable) -> list:
    return [room for room in rooms if ota_topic_matches_room(topic, room)]


def parse_ota_payload(payload: dict) -> OTAUpdate:
    if not isinstance(payload, dict):
        raise ValueError("OTA payload must be a JSON object")

    version = payload.get("version")
    if version is not None:
        version = str(version)

    raw_params = payload.get("params", {})
    if raw_params is None:
        raw_params = {}
    if not isinstance(raw_params, dict):
        raise ValueError("OTA params must be an object")

    params: dict[str, float] = {}
    for key, value in raw_params.items():
        if key not in ALLOWED_OTA_PARAMS:
            raise ValueError(f"Unsupported OTA parameter: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"OTA parameter {key} must be numeric")
        params[key] = float(value)

    if version is None and not params:
        raise ValueError("OTA payload must include version or params")

    return OTAUpdate(version=version, params=params)


def apply_ota_update(room, payload: dict) -> OTAUpdate:
    update = parse_ota_payload(payload)
    room.apply_ota_update(version=update.version, params=update.params)
    return update
