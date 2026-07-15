#!/usr/bin/env python3
"""Test cách ly topic giữa các device"""
import paho.mqtt.client as mqtt
import time, json, threading

BROKER = "10.140.222.156"
PORT = 1883
results = []

def test_publish(user, password, topic, msg, expect_success=True):
    """Test 1 device publish lên 1 topic"""
    connected = threading.Event()
    pub_result = {"user": user, "topic": topic, "status": "unknown"}
    
    def on_connect(client, ud, flags, rc, props=None):
        if rc == 0:
            connected.set()
        else:
            pub_result["status"] = f"connect_failed (rc={rc})"
            connected.set()
    
    def on_publish(client, ud, mid, rc=None, props=None):
        pub_result["status"] = "published"
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test_{user}")
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        client.connect(BROKER, PORT)
        client.loop_start()
        connected.wait(3)
        
        if "failed" not in pub_result["status"]:
            result = client.publish(topic, json.dumps({"value": msg}), qos=1)
            result.wait_for_publish(timeout=3)
            if pub_result["status"] != "published":
                pub_result["status"] = "published (qos1)"
    except Exception as e:
        pub_result["status"] = f"error: {e}"
    finally:
        client.loop_stop()
        client.disconnect()
    
    results.append(pub_result)
    return pub_result

def test_subscribe(user, password, topic, wait_sec=3):
    """Test 1 device subscribe 1 topic, đợi message"""
    messages = []
    connected = threading.Event()
    
    def on_connect(client, ud, flags, rc, props=None):
        if rc == 0:
            client.subscribe(topic)
            connected.set()
        else:
            connected.set()
    
    def on_message(client, ud, msg):
        messages.append({"topic": msg.topic, "payload": msg.payload.decode()})
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sub_{user}")
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER, PORT)
        client.loop_start()
        connected.wait(3)
        time.sleep(wait_sec)
    except Exception as e:
        print(f"  Subscribe error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
    
    return messages

print("=" * 60)
print("TEST 1: TD001 publish lên station/TD001/data (topic của nó)")
print("=" * 60)
r = test_publish("TD001", "Test@12345", "station/TD001/data", "temp=25.5")
print(f"  Kết quả: {r['status']}")

print()
print("=" * 60)
print("TEST 2: TD001 publish lên station/TD002/data (topic của TD002)")
print("=" * 60)
r = test_publish("TD001", "Test@12345", "station/TD002/data", "HACK!")
print(f"  Kết quả: {r['status']}")

print()
print("=" * 60)
print("TEST 3: TD002 subscribe station/TD001/# (topic của TD001)")
print("=" * 60)
# Trước tiên TD001 publish data
def bg_publish():
    time.sleep(1)
    test_publish("TD001", "Test@12345", "station/TD001/data", "realdata")

t = threading.Thread(target=bg_publish)
t.start()
msgs = test_subscribe("TD002", "Test@12345", "station/TD001/#", wait_sec=3)
t.join()
print(f"  TD002 nhận được {len(msgs)} message từ station/TD001/#")
if msgs:
    for m in msgs:
        print(f"    - {m['topic']}: {m['payload']}")
else:
    print(f"  → TD002 KHÔNG đọc được topic của TD001 ✅ (cách ly OK)")

print()
print("=" * 60)
print("TEST 4: django_backend subscribe station/# (tất cả)")
print("=" * 60)
def bg_publish2():
    time.sleep(1)
    test_publish("TD001", "Test@12345", "station/TD001/data", "from_TD001")
    test_publish("TD002", "Test@12345", "station/TD002/data", "from_TD002")

t = threading.Thread(target=bg_publish2)
t.start()
msgs = test_subscribe("django_backend", "Django@12345", "station/#", wait_sec=4)
t.join()
print(f"  Backend nhận được {len(msgs)} messages")
for m in msgs:
    print(f"    - {m['topic']}: {m['payload']}")

print()
print("=" * 60)
print("TỔNG KẾT")
print("=" * 60)
