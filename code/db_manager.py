import sqlite3
import threading
import time

class DBManager:
    def __init__(self, db_path="state.db"):
        self.db_path = db_path
        
        self.lock = threading.Lock()
        self.rooms = {}
        self.unsaved_rooms = set()
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        con = self.get_connection()
        cursor = con.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS room_states (
                room_id TEXT PRIMARY KEY,
                last_temp REAL,
                last_humidity REAL,
                hvac_mode TEXT,
                target_temp REAL,
                last_update INTEGER
            )
        ''')
        con.commit()
        con.close()
        print("DB initialized")

    def generate_expected_rooms(self, max_floors=5, rooms_per_floor=40):
        room_ids = []
        for f in range(1, max_floors + 1):
            for r in range(1, rooms_per_floor + 1):
                room_num = (f * 100) + r
                room_ids.append(f"b01-f{f:02d}-r{room_num}")
        return room_ids

    def load_state(self, expected_room_ids=None):
        if expected_room_ids is None:
            expected_room_ids = self.generate_expected_rooms()

        con = self.get_connection()
        cursor = con.cursor()
        
        cursor.execute("SELECT room_id, last_temp, last_humidity, hvac_mode, target_temp, last_update FROM room_states")
        rows = cursor.fetchall()
        
        loaded_rooms = {row[0]: row for row in rows}
        
        now = int(time.time())
        defaults = {
            "last_temp": 22.0,
            "last_humidity": 50.0,
            "hvac_mode": "ECO",
            "target_temp": 22.0,
            "last_update": now
        }

        with self.lock:
            for rid in expected_room_ids:
                if rid in loaded_rooms:
                    row = loaded_rooms[rid]
                    self.rooms[rid] = {
                        "room_id": rid,
                        "last_temp": float(row[1]) if row[1] is not None else 22.0,
                        "last_humidity": float(row[2]) if row[2] is not None else 50.0,
                        "hvac_mode": str(row[3]) if row[3] is not None else "ECO",
                        "target_temp": float(row[4]) if row[4] is not None else 22.0,
                        "last_update": int(row[5]) if row[5] is not None else now
                    }
                else:
                    self.rooms[rid] = {
                        "room_id": rid,
                        **defaults
                    }
                    self.unsaved_rooms.add(rid)

        if self.unsaved_rooms:
            to_sync = []
            for rid in self.unsaved_rooms:
                room = self.rooms[rid]
                to_sync.append((
                    room["room_id"], room["last_temp"], room["last_humidity"],
                    room["hvac_mode"], room["target_temp"], room["last_update"]
                ))
            cursor.executemany('''
                INSERT OR REPLACE INTO room_states (room_id, last_temp, last_humidity, hvac_mode, target_temp, last_update)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', to_sync)
            con.commit()
            print(f"Injected defaults for {len(to_sync)} missing rooms")
            
        con.close()
        return self.rooms

    def update_room(self, room_id, last_temp=None, last_humidity=None, hvac_mode=None, target_temp=None, timestamp=None):
        with self.lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = {
                    "room_id": room_id,
                    "last_temp": 22.0, "last_humidity": 50.0,
                    "hvac_mode": "ECO", "target_temp": 22.0,
                    "last_update": int(time.time())
                }

            if last_temp is not None:
                self.rooms[room_id]["last_temp"] = float(last_temp)
            if last_humidity is not None:
                self.rooms[room_id]["last_humidity"] = float(last_humidity)
            if hvac_mode is not None:
                self.rooms[room_id]["hvac_mode"] = str(hvac_mode)
            if target_temp is not None:
                self.rooms[room_id]["target_temp"] = float(target_temp)
                
            self.rooms[room_id]["last_update"] = int(timestamp) if timestamp else int(time.time())
            
            self.unsaved_rooms.add(room_id)

    def _sync_impl(self, con):
        if not self.unsaved_rooms:
            return
            
        to_sync = []
        with self.lock:
            for rid in self.unsaved_rooms:
                room = self.rooms[rid]
                to_sync.append((
                    room["room_id"],
                    room["last_temp"],
                    room["last_humidity"],
                    room["hvac_mode"],
                    room["target_temp"],
                    room["last_update"]
                ))
            self.unsaved_rooms.clear()

        cursor = con.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO room_states (room_id, last_temp, last_humidity, hvac_mode, target_temp, last_update)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', to_sync)
        con.commit()
        print(f"Synced {len(to_sync)} rooms to DB")

    def save_room_immediate(self, room_id):
        # might be called from an MQTT callback thread
        con = self.get_connection()
        cursor = con.cursor()
        
        with self.lock:
            if room_id not in self.rooms:
                con.close()
                return
            room = self.rooms[room_id]
            data = (
                room["room_id"], room["last_temp"], room["last_humidity"],
                room["hvac_mode"], room["target_temp"], room["last_update"]
            )
            if room_id in self.unsaved_rooms:
                self.unsaved_rooms.remove(room_id)
                
        cursor.execute('''
            INSERT OR REPLACE INTO room_states (room_id, last_temp, last_humidity, hvac_mode, target_temp, last_update)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', data)
        con.commit()
        con.close()
        print(f"Immediate save executed for {room_id}")

    def start_background_sync(self, sync_interval=30):
        def sync_worker():
            con = self.get_connection()
            while True:
                time.sleep(sync_interval)
                try:
                    self._sync_impl(con)
                except Exception as e:
                    print(f"Sync error: {e}")
                
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
        print(f"Background sync started ({sync_interval}s interval)")

if __name__ == "__main__":
        db = DBManager()
        rooms = db.load_state()
        print(f"Loaded {len(rooms)} rooms into memory")
        
        # test
        db.start_background_sync(sync_interval=2) 
        
        db.update_room("b01-f01-r101", last_temp=24.5)
        db.update_room("b01-f01-r102", last_temp=25.0)
        
        time.sleep(3)
        
        db.update_room("b01-f05-r502", hvac_mode="ON", target_temp=20.0)
        db.save_room_immediate("b01-f05-r502")
