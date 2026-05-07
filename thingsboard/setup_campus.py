import requests
import json

BASE_URL = "http://localhost:9090"
LOGIN_DATA = {"username": "tenant@thingsboard.org", "password": "tenant"}

auth_response = requests.post(f"{BASE_URL}/api/auth/login", json=LOGIN_DATA)
TOKEN = auth_response.json().get("token")
HEADERS = {
    'X-Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

def create_asset(name, profile, parent_id=None):
    asset_data = {"name": name, "type": profile}
    res = requests.post(f"{BASE_URL}/api/asset", headers=HEADERS, json=asset_data).json()
    asset_id = res['id']['id']
    print(f"Created {profile}: {name} ({asset_id})")

    if parent_id:
        rel_data = {
            "from": {"id": parent_id, "entityType": "ASSET"},
            "to": {"id": asset_id, "entityType": "ASSET"},
            "type": "Contains"
        }
        requests.post(f"{BASE_URL}/api/relation", headers=HEADERS, json=rel_data)
    return asset_id

campus_id = create_asset("ZC-Main-Campus", "campus")
bldg_id = create_asset("B01", "building", campus_id)

for f in range(1, 11):
    floor_id = create_asset(f"B01-F{f:02}", "floor", bldg_id)
    
    for r in range(1, 21):
        room_name = f"B01-F{f:02}-R{r:03}"
        room_id = create_asset(room_name, "room", floor_id)
        
        attr_data = {
            "square_footage": 45,
            "occupant_capacity": 30,
            "coordinates_x": 100 + (r * 20),
            "coordinates_y": 100 + (f * 20),
            "room_type": "lab"
        }
        requests.post(
            f"{BASE_URL}/api/plugins/telemetry/ASSET/{room_id}/attributes/SERVER_SCOPE",
            headers=HEADERS, json=attr_data
        )