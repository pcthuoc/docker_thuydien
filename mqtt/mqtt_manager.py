#!/usr/bin/env python3
"""
Quản lý Mosquitto Dynamic Security qua MQTT Topic API
Không cần docker exec - kết nối trực tiếp qua MQTT

Usage:
    python mqtt_manager.py list-clients
    python mqtt_manager.py create-device <username> <password>
    python mqtt_manager.py disable-device <username>
    python mqtt_manager.py enable-device <username>
    python mqtt_manager.py delete-device <username>
    python mqtt_manager.py get-client <username>
    python mqtt_manager.py list-roles
    python mqtt_manager.py list-groups
    python mqtt_manager.py setup-roles    (tạo roles/groups cho thủy điện)
"""

import sys
import json
import time
import paho.mqtt.client as mqtt

# ========== CẤU HÌNH ==========
BROKER_HOST = "10.140.222.156"
BROKER_PORT = 1883
ADMIN_USER = "admin"
ADMIN_PASS = "Admin@Mqtt2026"

CONTROL_TOPIC = "$CONTROL/dynamic-security/v1"
RESPONSE_TOPIC = "$CONTROL/dynamic-security/v1/response"
# ===============================

response_received = False
response_data = None


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(RESPONSE_TOPIC)
    else:
        print(f"Kết nối thất bại, code: {rc}")
        sys.exit(1)


def on_message(client, userdata, msg):
    global response_received, response_data
    response_data = json.loads(msg.payload.decode())
    response_received = True


def send_command(commands):
    """Gửi lệnh đến Dynamic Security Plugin và nhận response"""
    global response_received, response_data
    response_received = False
    response_data = None

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(ADMIN_USER, ADMIN_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT)
    client.loop_start()

    time.sleep(0.5)  # Đợi subscribe

    payload = {"commands": commands}
    client.publish(CONTROL_TOPIC, json.dumps(payload))

    # Đợi response
    timeout = 5
    start = time.time()
    while not response_received and (time.time() - start) < timeout:
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()

    if response_data:
        return response_data
    else:
        print("Không nhận được response (timeout)")
        return None


def print_response(data):
    """In response đẹp"""
    if not data:
        return
    responses = data.get("responses", [])
    for r in responses:
        cmd = r.get("command", "")
        if "error" in r:
            print(f"  ❌ {cmd}: {r['error']}")
        else:
            print(f"  ✅ {cmd}: OK")
            # In data nếu có
            for key in ["clients", "groups", "roles", "client", "group", "role"]:
                if key in r:
                    print(json.dumps(r[key], indent=2, ensure_ascii=False))


# ========== COMMANDS ==========

def list_clients():
    """Liệt kê tất cả clients"""
    print("=== Danh sách clients ===")
    data = send_command([{"command": "listClients"}])
    if data:
        for r in data.get("responses", []):
            clients = r.get("clients", [])
            for c in clients:
                print(f"  - {c}")
            print(f"Tổng: {len(clients)}")


def create_device(username, password):
    """Tạo device mới và thêm vào group devices"""
    print(f"=== Tạo device: {username} ===")
    data = send_command([
        {
            "command": "createClient",
            "username": username,
            "password": password,
            "groups": [{"groupname": "devices", "priority": -1}]
        }
    ])
    print_response(data)


def disable_device(username):
    """Khóa device - disconnect ngay lập tức"""
    print(f"=== Khóa device: {username} ===")
    data = send_command([{"command": "disableClient", "username": username}])
    print_response(data)


def enable_device(username):
    """Mở khóa device"""
    print(f"=== Mở khóa device: {username} ===")
    data = send_command([{"command": "enableClient", "username": username}])
    print_response(data)


def delete_device(username):
    """Xóa device vĩnh viễn"""
    print(f"=== Xóa device: {username} ===")
    data = send_command([{"command": "deleteClient", "username": username}])
    print_response(data)


def get_client(username):
    """Xem thông tin chi tiết 1 client"""
    print(f"=== Thông tin: {username} ===")
    data = send_command([{"command": "getClient", "username": username}])
    print_response(data)


def list_roles():
    """Liệt kê tất cả roles"""
    print("=== Danh sách roles ===")
    data = send_command([{"command": "listRoles"}])
    if data:
        for r in data.get("responses", []):
            roles = r.get("roles", [])
            for role in roles:
                print(f"  - {role}")


def list_groups():
    """Liệt kê tất cả groups"""
    print("=== Danh sách groups ===")
    data = send_command([{"command": "listGroups"}])
    if data:
        for r in data.get("responses", []):
            groups = r.get("groups", [])
            for g in groups:
                print(f"  - {g}")


def setup_roles():
    """Tạo roles và groups cho hệ thống thủy điện"""
    print("=== Thiết lập roles/groups cho thủy điện ===")

    commands = [
        # Role: device publish data lên topic của mình
        {"command": "createRole", "rolename": "device_publish"},
        {"command": "addRoleACL", "rolename": "device_publish",
         "acltype": "publishClientSend", "topic": "station/%u/data",
         "allow": True, "priority": 1},
        {"command": "addRoleACL", "rolename": "device_publish",
         "acltype": "publishClientSend", "topic": "station/%u/status",
         "allow": True, "priority": 2},

        # Role: device subscribe topic của mình
        {"command": "createRole", "rolename": "device_subscribe"},
        {"command": "addRoleACL", "rolename": "device_subscribe",
         "acltype": "subscribePattern", "topic": "station/%u/#",
         "allow": True, "priority": 1},
        {"command": "addRoleACL", "rolename": "device_subscribe",
         "acltype": "publishClientReceive", "topic": "station/%u/#",
         "allow": True, "priority": 1},

        # Role: backend full access
        {"command": "createRole", "rolename": "backend_full"},
        {"command": "addRoleACL", "rolename": "backend_full",
         "acltype": "subscribePattern", "topic": "station/#",
         "allow": True, "priority": 1},
        {"command": "addRoleACL", "rolename": "backend_full",
         "acltype": "publishClientReceive", "topic": "station/#",
         "allow": True, "priority": 1},
        {"command": "addRoleACL", "rolename": "backend_full",
         "acltype": "publishClientSend", "topic": "station/#",
         "allow": True, "priority": 1},

        # Group: devices
        {"command": "createGroup", "groupname": "devices"},
        {"command": "addGroupRole", "groupname": "devices",
         "rolename": "device_publish", "priority": 1},
        {"command": "addGroupRole", "groupname": "devices",
         "rolename": "device_subscribe", "priority": 2},

        # Group: backends
        {"command": "createGroup", "groupname": "backends"},
        {"command": "addGroupRole", "groupname": "backends",
         "rolename": "backend_full", "priority": 1},
    ]

    data = send_command(commands)
    print_response(data)
    print("\nRoles/groups đã sẵn sàng!")
    print("Tạo device:  python mqtt_manager.py create-device device_001 matkhau123456")
    print("Tạo backend: python mqtt_manager.py create-backend django matkhau123456")


def create_backend(username, password):
    """Tạo backend client (Django) với full access"""
    print(f"=== Tạo backend client: {username} ===")
    data = send_command([
        {
            "command": "createClient",
            "username": username,
            "password": password,
            "groups": [{"groupname": "backends", "priority": -1}]
        }
    ])
    print_response(data)


# ========== MAIN ==========

def usage():
    print("""
Mosquitto Dynamic Security Manager

Commands:
  list-clients                     Liệt kê clients
  list-roles                       Liệt kê roles
  list-groups                      Liệt kê groups
  get-client <username>            Xem thông tin client
  setup-roles                      Tạo roles/groups cho thủy điện
  create-device <user> <pass>      Tạo device mới
  create-backend <user> <pass>     Tạo backend client (Django)
  disable-device <username>        Khóa device
  enable-device <username>         Mở khóa device
  delete-device <username>         Xóa device

Ví dụ:
  python mqtt_manager.py setup-roles
  python mqtt_manager.py create-device device_001 matkhau123456
  python mqtt_manager.py list-clients
  python mqtt_manager.py disable-device device_001
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list-clients":
        list_clients()
    elif cmd == "list-roles":
        list_roles()
    elif cmd == "list-groups":
        list_groups()
    elif cmd == "get-client" and len(sys.argv) >= 3:
        get_client(sys.argv[2])
    elif cmd == "setup-roles":
        setup_roles()
    elif cmd == "create-device" and len(sys.argv) >= 4:
        create_device(sys.argv[2], sys.argv[3])
    elif cmd == "create-backend" and len(sys.argv) >= 4:
        create_backend(sys.argv[2], sys.argv[3])
    elif cmd == "disable-device" and len(sys.argv) >= 3:
        disable_device(sys.argv[2])
    elif cmd == "enable-device" and len(sys.argv) >= 3:
        enable_device(sys.argv[2])
    elif cmd == "delete-device" and len(sys.argv) >= 3:
        delete_device(sys.argv[2])
    else:
        usage()
