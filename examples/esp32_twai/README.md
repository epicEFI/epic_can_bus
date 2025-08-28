# ESP32 (TWAI) Examples

Hardware
- ESP32 with built-in TWAI (CAN) peripheral
- Transceiver like SN65HVD230 required

Sketches
- read_vars_serial.cpp: Reads variables and prints to Serial.
- send_setLuaGauge_analog.cpp: Reads ADC and sends setLuaGauge.
- send_setLuaGauge_digital.cpp: Reads digital input and sends setLuaGauge.
- freq_input_setLuaGauge.cpp: Measures frequency using hardware timer/interrupt, sends to setLuaGauge.
- pwm_from_boostOutput.cpp: Reads boostOutput and sets PWM duty on a pin.

Reference
See ../../Docs/packet_basics.md for packet formats.
