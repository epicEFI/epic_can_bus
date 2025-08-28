#!/usr/bin/env python3
import socket
import struct
import json
from pathlib import Path

_FMT = '=IB3x8s'

def can_socket(iface: str = 'can0') -> socket.socket:
    s = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    s.bind((iface,))
    return s

def send_frame(sock: socket.socket, can_id: int, data: bytes) -> None:
    dlc = len(data)
    if dlc > 8:
        raise ValueError('DLC > 8 not supported in classic CAN')
    frame = struct.pack(_FMT, can_id, dlc, data + bytes(8 - dlc))
    sock.send(frame)

def recv_frame(sock: socket.socket) -> tuple[int, int, bytes]:
    pkt = sock.recv(16)
    can_id, dlc, payload = struct.unpack(_FMT, pkt)
    return can_id, dlc, payload

# ----- Variable hashing (djb2lowerCase) -----

def djb2lowercase(name: str) -> int:
    """Compute rusEFI djb2lowerCase signed 32-bit hash for a variable name."""
    h = 5381
    for ch in name:
        c = ord(ch.lower())
        h = ((h << 5) + h + c) & 0xFFFFFFFF  # 32-bit wrap
    # convert to signed int32
    if h & 0x80000000:
        h = -((~h + 1) & 0xFFFFFFFF)
    return h

# ----- Variables (0x700/0x720 + ecu) -----

def send_variable_request(sock: socket.socket, var_hash: int, dest: int = 0, src: int = 1) -> None:
    can_id = 0x700 + (dest & 0x0F)
    data = struct.pack('>i', int(var_hash))
    send_frame(sock, can_id, data)

def recv_variable_response(sock: socket.socket, expected_hash: int | None = None, src_ecu: int | None = None) -> tuple[int, int, float]:
    while True:
        rx_id, dlc, payload = recv_frame(sock)
        # Expect response at 0x720 + ecuId; if src_ecu provided, filter that id
        if (rx_id & 0x7F0) != 0x720:
            continue
        if src_ecu is not None and rx_id != (0x720 + (src_ecu & 0x0F)):
            continue
        hash_i32 = struct.unpack('>i', payload[0:4])[0]
        if expected_hash is not None and hash_i32 != int(expected_hash):
            continue
        value = struct.unpack('>f', payload[4:8])[0]
        return rx_id, hash_i32, value

def get_variable(sock: socket.socket, var_hash: int, dest: int = 0, src: int = 1):
    send_variable_request(sock, var_hash, dest, src)
    _, _, value = recv_variable_response(sock, expected_hash=var_hash, src_ecu=dest if dest != 0 else None)
    return value

def get_variable_by_name(sock: socket.socket, var_name: str, dest: int = 0, src: int = 1):
    """Convenience: hash the name using djb2lowerCase and retrieve the variable."""
    h = djb2lowercase(var_name)
    return get_variable(sock, h, dest, src)

# ----- Functions (0x740/0x760 + ecu) -----

def _resolve_function_id(token: int | str) -> int:
    if isinstance(token, int):
        return token
    try:
        return int(token, 0)
    except Exception:
        pass
    # epic_can_bus root: .../epic_can_bus/examples/python/EpicECU/__init__.py -> parents[3]
    base = Path(__file__).resolve().parents[3]
    cfg = base / 'functions_v1.json'
    data = json.loads(cfg.read_text(encoding='utf-8')) if cfg.exists() else []
    for item in data:
        if item.get('luaName') == token:
            return int(item.get('id'))
    raise ValueError(f'Function not found: {token}')

def call_function(sock: socket.socket, func: int | str, arg_f32: float = 0.0, dest: int = 0, arg2_i16: int | None = None) -> float:
    func_id = _resolve_function_id(func)
    can_id = 0x740 + (dest & 0x0F)
    # Frame: [0..1] funcId, [2..5] float32 arg1, [6..7] optional int16 arg2
    if arg2_i16 is None:
        data = struct.pack('>Hf', func_id & 0xFFFF, float(arg_f32)) + bytes([0, 0])
        dlc = 6
    else:
        data = struct.pack('>Hf', func_id & 0xFFFF, float(arg_f32)) + struct.pack('>h', int(arg2_i16))
        dlc = 8
    # Pad to dlc (kernel packs full 8 anyway)
    send_frame(sock, can_id, data)
    # Wait for response and return float (0x760 + ecuId)
    while True:
        rx_id, dlc, payload = recv_frame(sock)
        expected = 0x760 + (dest & 0x0F)
        if rx_id != expected:
            continue
        fid = struct.unpack('>H', payload[0:2])[0]
        if fid != (func_id & 0xFFFF):
            continue
        ret = struct.unpack('>f', payload[4:8])[0]
        return ret

# ----- Variable set (0x780 + ecu_addr) -----

def set_variable(sock: socket.socket, var_hash: int, value: float, ecu_addr: int = 0) -> None:
    """Send a fire-and-forget variable set to 0x780 + ecu_addr.

    Payload: [0..3] VarHash (int32 BE), [4..7] Value (float32 BE)
    """
    can_id = 0x780 + (ecu_addr & 0x0F)
    data = struct.pack('>if', int(var_hash), float(value))
    send_frame(sock, can_id, data)

def set_variable_by_name(sock: socket.socket, name: str, value: float, ecu_addr: int = 0) -> None:
    """Hash the variable name and send a set request (fire-and-forget)."""
    h = djb2lowercase(name)
    set_variable(sock, h, value, ecu_addr)

