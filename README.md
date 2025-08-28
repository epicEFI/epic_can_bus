# EPIC Over CANbus - SBC Client Guide (Raspberry Pi, Jetson, etc.)

## Prerequisites
- Linux SBC with CAN interface (native CAN or USB-CAN adapter)
- Kernel with SocketCAN (most modern Raspberry Pi OS/Ubuntu have it)
- Python 3.8+

Install python-can:
```bash
python3 -m pip install --user python-can
```

## Wiring
- Connect ECU CAN-H to adapter CAN-H
- Connect ECU CAN-L to adapter CAN-L
- Ensure proper termination: 120Ω at both ends of the CAN bus

## Bring up CAN (SocketCAN)
Use the helper script (defaults to can0 at 500k):
```bash
./epic_can_bus/scripts/can0_up.sh
```
Or manually:
```bash
sudo ip link set can0 down || true
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
ip -details -statistics link show can0
```

## Variable read example (0x700/0x720 + ecu)
1) Find the variable hash (generate docs):
```bash
python3 epic_can_bus/gen_variables.py
less epic_can_bus/Docs/variables.md
```
- Note: Hash values are signed 32-bit integers. Pass negative hashes as-is (e.g., -230533156).

2) Query a variable by hash:
```bash
python3 epic_can_bus/examples/python/get_var.py <ecu_addr:0..15> <var_name | hash:int>
```
- Input (CAN TX): ID 0x700 + ecuId, payload:
  - [0..3] VarHash (int32 big-endian, two's complement)
- Output (CAN RX): ID 0x720 + ecuId (float32), payload:
  - [0..3] VarHash (int32 big-endian)
  - [4..7] float32 value (big-endian)
- Expected console output: single number (float). If the ECU responds with zero-as-error for not-found, you'll see 0.0

## Function call example (0x740/0x760+ecu)
1) Generate functions JSON from the v1 registry:
```bash
python3 epic_can_bus/gen_functions.py
less epic_can_bus/functions_v1.json
```
2) Call a function:
```bash
# by id
python3 epic_can_bus/examples/python/call_func.py <dest_ecu> 10
# by name
python3 epic_can_bus/examples/python/call_func.py <dest_ecu> setFuelAdd 4
```
- Input (CAN TX): ID 0x740 + ecuId, payload:
  - [0..1] FunctionID (u16, big-endian)
  - [2..5] Arg1 (float32)
  - [6..7] optional Arg2 (int16)
- Output (CAN RX): ID 0x760 + ecuId, payload:
  - [0..1] FunctionID (u16, big-endian)
  - [2..3] reserved
  - [4..7] Return float32 (big-endian)

## Writing variables (0x780 + ecuCanId)
Send a single frame to CAN ID `0x780 + ecuCanId`:
```
Data: [0..3] VarHash (int32 BE), [4..7] Value (float32 BE)
```
No ACK is sent (fire-and-forget).

## Troubleshooting
- No response: verify wiring, termination, correct bitrate, and that ECU firmware has EPIC Over CANbus enabled.
- Always 0.0 for variables: wrong hash or variable not available; regenerate `Docs/variables.md` after building firmware.
- Function calls return 0: ensure the called function exists in the registry and returns a value.

## Notes
- All multi-byte fields are big-endian on the wire.
- Responses are sent on the same CAN bus as the request.
- v1 uses float32 for variables only (no int responses).
- Errors are indicated by zero data; clients should handle defensively.
