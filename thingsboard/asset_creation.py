import requests
import random

TB_URL = "http://localhost:9090"
USERNAME = "tenant@thingsboard.org"
PASSWORD = "tenant"

# --- Auth ---
r = requests.post(f"{TB_URL}/api/auth/login",
                  json={"username": USERNAME, "password": PASSWORD})
token = r.json()["token"]
print("Token:", token)
headers = {"X-Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# --- Helpers ---
def create_asset(name, asset_type):
    r = requests.post(f"{TB_URL}/api/asset", headers=headers, json={
        "name": name,
        "label": asset_type,   # just a label, not a registered type
        "type": asset_type
    })
    print(f"{r.status_code}: {r.json()}")
    return r.json()["id"]["id"]

def create_relation(from_id, from_type, to_id, to_type):
    requests.post(f"{TB_URL}/api/relation", headers=headers, json={
        "from": {"id": from_id, "entityType": from_type},
        "to":   {"id": to_id,   "entityType": to_type},
        "type": "Contains",
        "typeGroup": "COMMON"
    })

def get_device_id(device_name):
    r = requests.get(f"{TB_URL}/api/tenant/devices?deviceName={device_name}", headers=headers)
    if r.status_code != 200 or "id" not in r.json():
        print(f"WARNING: Device not found: {device_name}")
        return None
    return r.json()["id"]["id"]

def set_room_attributes(asset_id, floor, room_offset):
    ROOM_TYPES = ["lecture_hall", "lab", "office", "corridor"]
    requests.post(
        f"{TB_URL}/api/plugins/telemetry/ASSET/{asset_id}/attributes/SERVER_SCOPE",
        headers=headers,
        json={
            "square_footage": random.choice([30, 45, 60, 80]),
            "occupant_capacity": random.choice([10, 20, 30, 40]),
            "coordinates_x": (room_offset % 5) * 120 + 60,
            "coordinates_y": (room_offset // 5) * 120 + 60,
            "room_type": ROOM_TYPES[(floor + room_offset) % len(ROOM_TYPES)]
        }
    )

# --- Build Hierarchy ---
campus_id = create_asset("ZC-Main-Campus", "campus")
print("Created campus")

b01_id = create_asset("B01", "building")
create_relation(campus_id, "ASSET", b01_id, "ASSET")
print("Created building B01")

for floor in range(1, 11):
    floor_id = create_asset(f"B01-F{floor:02d}", "floor")
    create_relation(b01_id, "ASSET", floor_id, "ASSET")
    print(f"Created floor B01-F{floor:02d}")

    for room_offset in range(10):

        # MQTT room
        mqtt_room_num = floor * 100 + room_offset + 1
        mqtt_asset_id = create_asset(f"B01-F{floor:02d}-R{mqtt_room_num}", "room")
        create_relation(floor_id, "ASSET", mqtt_asset_id, "ASSET")
        set_room_attributes(mqtt_asset_id, floor, room_offset)

        mqtt_device_id = get_device_id(f"MQTT-F{floor:02d}-R{mqtt_room_num}")
        if mqtt_device_id:
            create_relation(mqtt_asset_id, "ASSET", mqtt_device_id, "DEVICE")

        # CoAP room
        coap_room_num = floor * 100 + room_offset + 101
        coap_asset_id = create_asset(f"B01-F{floor:02d}-R{coap_room_num}", "room")
        create_relation(floor_id, "ASSET", coap_asset_id, "ASSET")
        set_room_attributes(coap_asset_id, floor, room_offset + 10)

        coap_device_id = get_device_id(f"CoAP-F{floor:02d}-R{coap_room_num}")
        if coap_device_id:
            create_relation(coap_asset_id, "ASSET", coap_device_id, "DEVICE")

    print(f"Floor {floor:02d} done — 20 room assets created and linked")

print("\nDone. Full hierarchy built.")