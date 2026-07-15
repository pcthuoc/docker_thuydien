# MQTT Mosquitto - Hệ thống Thủy điện

## Kiến trúc

```
                    ┌─────────────────────────┐
                    │   Mosquitto Broker       │
                    │   10.140.222.156:1883    │
                    │   Dynamic Security Plugin│
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │  Device    │ │  Device    │ │  Django    │
        │  TD001     │ │  TD002     │ │  Backend   │
        │            │ │            │ │  (admin)   │
        └────────────┘ └────────────┘ └────────────┘
```

## Tài khoản

| Vai trò | Username | Password | Quyền |
|---------|----------|----------|-------|
| **Backend (Django)** | `admin` | `Admin@Mqtt2026` | Superuser - full access mọi topic + quản lý Dynamic Security |
| **Device** | `{device_id}` | Tạo khi add device | Chỉ pub/sub `station/{device_id}/#` |

## Topic Structure

```
station/
├── {device_id}/
│   ├── data        ← Device gửi dữ liệu sensor
│   └── status      ← Device gửi trạng thái online/offline
```

## Phân quyền (ACL)

### Roles

| Role | Quyền | Topic Pattern |
|------|-------|---------------|
| `device_publish` | publishClientSend | `station/%u/data`, `station/%u/status` |
| `device_subscribe` | subscribePattern + publishClientReceive | `station/%u/#` |
| `backend_full` | subscribe + publish + receive | `station/#` |

> `%u` = Mosquitto tự thay bằng username của client đang kết nối

### Groups

| Group | Roles | Mô tả |
|-------|-------|-------|
| `devices` | device_publish, device_subscribe | Mỗi device chỉ truy cập topic của chính nó |
| `backends` | backend_full | Full access tất cả station (không cần vì admin đã là superuser) |

## Cách ly Topic (Đã test)

| Hành động | Kết quả |
|-----------|---------|
| TD001 publish `station/TD001/data` | ✅ Thành công |
| TD001 publish `station/TD002/data` | ❌ Broker drop (không có quyền) |
| TD002 subscribe `station/TD001/#` | ❌ Không nhận được message |
| Backend subscribe `station/#` | ✅ Nhận được tất cả |

## Quản lý bằng mqtt_manager.py

### Cài đặt ban đầu (chỉ chạy 1 lần)

```bash
python3 mqtt_manager.py setup-roles
```

### Thêm device mới

```bash
python3 mqtt_manager.py create-device {device_id} {password}
# Ví dụ:
python3 mqtt_manager.py create-device TD001 MatKhau@123
```

### Các lệnh khác

```bash
python3 mqtt_manager.py list-clients          # Xem tất cả clients
python3 mqtt_manager.py get-client TD001      # Xem chi tiết 1 client
python3 mqtt_manager.py disable-device TD001  # Khóa device (disconnect ngay)
python3 mqtt_manager.py enable-device TD001   # Mở khóa device
python3 mqtt_manager.py delete-device TD001   # Xóa device vĩnh viễn
python3 mqtt_manager.py list-roles            # Xem roles
python3 mqtt_manager.py list-groups           # Xem groups
```

## Django Backend sử dụng MQTT

Django kết nối broker với account `admin`:

```python
MQTT_BROKER = "10.140.222.156"
MQTT_PORT = 1883
MQTT_USER = "admin"
MQTT_PASS = "Admin@Mqtt2026"

# Subscribe nhận data từ tất cả device
client.subscribe("station/#")

# Tạo device mới qua Dynamic Security API
client.publish("$CONTROL/dynamic-security/v1", json.dumps({
    "commands": [{
        "command": "createClient",
        "username": device_id,
        "password": password,
        "groups": [{"groupname": "devices", "priority": -1}]
    }]
}))
```

## Luồng dữ liệu

```
Device (TD001)                    Broker                      Django Backend
    │                               │                              │
    │── publish ──────────────────►│                              │
    │   station/TD001/data         │── forward ─────────────────►│
    │   {"temp": 25.5, ...}        │   station/TD001/data        │
    │                               │                              │
    │                               │◄── publish ─────────────────│
    │◄── forward ──────────────────│   station/TD001/command     │
    │   station/TD001/command      │                              │
```
