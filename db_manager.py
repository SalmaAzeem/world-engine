import sqlite3
import threading
import time

class DBManager:
    def __init__(self, db_path="state.db"):
        self.db_path = db_path
        
        self.lock = threading.Lock()
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

if __name__ == "__main__":
    db = DBManager()
