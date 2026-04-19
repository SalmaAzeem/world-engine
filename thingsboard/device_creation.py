import requests, csv, json

TB_URL = "http://localhost:9090"
USERNAME = "tenant@thingsboard.org"
PASSWORD = "tenant"

# --- Auth ---
r = requests.post(f"{TB_URL}/api/auth/login",
                  json={"username": USERNAME, "password": PASSWORD})
token = r.json()["token"]
headers = {"X-Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# --- Get profile IDs ---
def get_profile_id(name):
    r = requests.get(f"{TB_URL}/api/deviceProfiles?pageSize=10&page=0", headers=headers)
    for p in r.json()["data"]:
        if p["name"] == name:
            return p["id"]["id"]

mqtt_profile_id = get_profile_id("MQTT-ThermalSensor")
coap_profile_id = get_profile_id("CoAP-ThermalSensor")

export_rows = []

for floor in range(1, 11):          # floors 1–10
    for room_offset in range(10):   # 10 MQTT rooms per floor

        # MQTT room: room 101–110, 201–210, etc.
        room_num = floor * 100 + room_offset + 1
        name = f"MQTT-F{floor:02d}-R{room_num}"
        payload = {
            "name": name,
            "type": "MQTT-ThermalSensor",
            "deviceProfileId": {"id": mqtt_profile_id, "entityType": "DEVICE_PROFILE"}
        }
        dev = requests.post(f"{TB_URL}/api/device", headers=headers, json=payload).json()
        dev_id = dev["id"]["id"]

        # Get access token
        creds = requests.get(f"{TB_URL}/api/device/{dev_id}/credentials", headers=headers).json()
        token_val = creds["credentialsId"]
        export_rows.append({"name": name, "protocol": "MQTT", "floor": floor,
                             "room": room_num, "token": token_val})

    for room_offset in range(10):   # 10 CoAP rooms per floor

        room_num = floor * 100 + room_offset + 101  # e.g. 201–210
        name = f"CoAP-F{floor:02d}-R{room_num}"
        payload = {
            "name": name,
            "type": "CoAP-ThermalSensor",
            "deviceProfileId": {"id": coap_profile_id, "entityType": "DEVICE_PROFILE"}
        }
        dev = requests.post(f"{TB_URL}/api/device", headers=headers, json=payload).json()
        dev_id = dev["id"]["id"]
        creds = requests.get(f"{TB_URL}/api/device/{dev_id}/credentials", headers=headers).json()
        token_val = creds["credentialsId"]
        export_rows.append({"name": name, "protocol": "CoAP", "floor": floor,
                             "room": room_num, "token": token_val})

# --- Export CSV ---
with open("devices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name","protocol","floor","room","token"])
    writer.writeheader()
    writer.writerows(export_rows)

print(f"Registered {len(export_rows)} devices. Tokens saved to devices.csv")