# Arduino (Longan Labs MCP_CAN) Examples

Hardware
- Arduino UNO/Nano + MCP2515 CAN shield (Longan Labs)
- 16MHz oscillator, CS pin D10 by default (adjust as needed)

Sketches
- read_vars_serial.ino: Reads select variables (RPMValue, TPSValue, AFRValue, ignition timing, injector PW) and prints to Serial.
- send_setLuaGauge_analog.ino: Reads analog pin A0, converts to volts, sends via call_function setLuaGauge(volts, id).
- send_setLuaGauge_digital.ino: Reads digital pin D2, sends 0.0/1.0 to setLuaGauge(id).
- freq_input_setLuaGauge.ino: Measures frequency on interrupt pin D2 and sends as Hz to setLuaGauge.
- pwm_from_boostOutput.ino: Reads boostOutput and sets PWM duty on a pin to match.

Reference
See ../../Docs/packet_basics.md for packet formats.
