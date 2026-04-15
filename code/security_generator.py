import json
import secrets
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent

def generate_credentials(config):
    building_id = config.get("building_id", "01")
    floors = config.get("floors", 10)
    rooms_per_floor = config.get("rooms_per_floor", 20)
    
    security_keys = {}
    
    # hivemq
    credentials = ET.Element("credentials")
    roles = ET.SubElement(credentials, "roles")
    users = ET.SubElement(credentials, "users")
    
    # subscriber
    master_role = ET.SubElement(roles, "role")
    ET.SubElement(master_role, "id").text = "master-subscriber"
    master_perms = ET.SubElement(master_role, "permissions")
    master_perm = ET.SubElement(master_perms, "permission")
    ET.SubElement(master_perm, "topic").text = "campus/#"
    ET.SubElement(master_perm, "action").text = "PUBLISH_SUBSCRIBE"
    
    # node
    node_role = ET.SubElement(roles, "role")
    ET.SubElement(node_role, "id").text = "node-role"
    node_perms = ET.SubElement(node_role, "permissions")
    
    #sub user
    master_pwd = secrets.token_hex(16)
    security_keys['subscriber'] = {"password": master_pwd}
    
    sub_user = ET.SubElement(users, "user")
    ET.SubElement(sub_user, "username").text = "subscriber"
    ET.SubElement(sub_user, "password").text = master_pwd
    sub_roles = ET.SubElement(sub_user, "roles")
    ET.SubElement(sub_roles, "role").text = "master-subscriber"
    
    for floor in range(1, floors + 1):
        for room in range(1, rooms_per_floor + 1):
            room_id = f"b{building_id}-f{floor:02d}-r{room}"
            mqtt_base_topic = f"campus/b{building_id}/f{floor:02d}/r{room}"
            
            pwd = secrets.token_hex(12)
            psk = secrets.token_hex(16) # DTLS
            
            security_keys[room_id] = {
                "password": pwd,
                "psk": psk
            }
            
            # create role
            r_role = ET.SubElement(roles, "role")
            ET.SubElement(r_role, "id").text = f"role-{room_id}"
            r_perms = ET.SubElement(r_role, "permissions")
            r_perm = ET.SubElement(r_perms, "permission")
            ET.SubElement(r_perm, "topic").text = f"{mqtt_base_topic}/#"
            ET.SubElement(r_perm, "action").text = "PUBLISH_SUBSCRIBE"
            
            # create user
            u_elem = ET.SubElement(users, "user")
            ET.SubElement(u_elem, "username").text = room_id
            ET.SubElement(u_elem, "password").text = pwd
            u_roles = ET.SubElement(u_elem, "roles")
            ET.SubElement(u_roles, "role").text = f"role-{room_id}"

    with open(BASE_DIR / "security_keys.json", "w") as f:
        json.dump(security_keys, f, indent=4)
        
    xmlstr = minidom.parseString(ET.tostring(credentials)).toprettyxml(indent="    ")
    with open(BASE_DIR.parent / "credentials.xml", "w") as f:
        f.write(xmlstr)

if __name__ == "__main__":
    with open(BASE_DIR / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    generate_credentials(config)
    print("[SECURITY] Generated security_keys.json and credentials.xml")
