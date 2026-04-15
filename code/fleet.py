from __future__ import annotations

from models.room_state import RoomState


def build_fleet(db_manager, config):
    _validate_config(config)

    states = db_manager.load_state()
    rooms = []
    coap_offset = 0

    for room_id in sorted(states.keys()):
        building_id, floor_id, room_number = parse_room_id(room_id)
        room_slot = room_number - (floor_id * 100)

        if room_slot <= config["mqtt_rooms_per_floor"]:
            protocol = "mqtt"
            coap_port = None
        else:
            protocol = "coap"
            coap_port = config["coap_base_port"] + coap_offset
            coap_offset += 1

        room_state = states[room_id]
        rooms.append(
            RoomState(
                building_id=building_id,
                floor_id=floor_id,
                room_number=room_number,
                protocol=protocol,
                temperature=room_state["last_temp"],
                humidity=room_state["last_humidity"],
                hvac_mode=room_state["hvac_mode"],
                target_temp=room_state["target_temp"],
                coap_host=config["coap_public_host"] if protocol == "coap" else None,
                coap_port=coap_port,
            )
        )

    return rooms


def parse_room_id(room_id):
    building, floor, room = room_id.split("-")
    return building[1:], int(floor[1:]), int(room[1:])


def _validate_config(config):
    expected_total = config["mqtt_rooms_per_floor"] + config["coap_rooms_per_floor"]
    if expected_total != config["rooms_per_floor"]:
        raise ValueError(
            "mqtt_rooms_per_floor + coap_rooms_per_floor must equal rooms_per_floor"
        )
