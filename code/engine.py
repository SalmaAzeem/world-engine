rooms = []
for f in range(1, 11):
    for r in range(1, 21):
        state = {
            "temperature": 22.0,
            "humidity": 50.0,
            "occupancy": False,
            "light_level": 100,
            "hvac_mode": "OFF"
        }
        rooms.append(Room("01", r, f, state))