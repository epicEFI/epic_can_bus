# EPIC Over CANbus v1 - Packet Basics (plain)

All multi-byte fields are big-endian. Classic CAN 11-bit identifiers.

- get_variable request (ID 0x700 + ecuId)
  - Data [0..3]: varHash int32 (signed)
- get_variable response (ID 0x720 + ecuId)
  - Data [0..3]: varHash int32 (same as request)
  - Data [4..7]: value float32

- set_variable request (ID 0x780 + (ecuCanId & 0x0F))
  - Data [0..3]: varHash int32 (signed)
  - Data [4..7]: value float32
  - Ack: none (fire-and-forget)

- call_function request (ID 0x740 + (ecuCanId & 0x0F))
  - Data [0..1]: functionId uint16
  - Data [2..5]: arg1 float32
  - Data [6..7]: arg2 int16 (optional; present if function expects 2 args)
- call_function response (ID 0x760 + ecuId)
  - Data [0..1]: functionId uint16
  - Data [2..3]: reserved (0)
  - Data [4..7]: return float32 (0.0 if no return)

Notes
- varHash is produced by djb2lowercase(name) and is signed int32.
- set_variable is per-ECU addressing via the CAN ID offset.
- call_function arg/ret are float32; some functions also take arg2=int16.
