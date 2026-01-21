# common/network.py
import json
import socket
from common.const import BUFFER_SIZE, FORMAT

def send_json(sock, data):
    """Gửi dictionary dưới dạng JSON string"""
    try:
        json_data = json.dumps(data)
        sock.send(json_data.encode(FORMAT))
    except Exception as e:
        print(f"Lỗi gửi tin: {e}")

def recv_json(sock):
    """Nhận và giải mã JSON"""
    try:
        data = sock.recv(BUFFER_SIZE).decode(FORMAT)
        if not data: return None
        return json.loads(data)
    except json.JSONDecodeError:
        return None
    except Exception as e:
        # print(f"Lỗi nhận tin: {e}") # Có thể bỏ comment để debug
        return None