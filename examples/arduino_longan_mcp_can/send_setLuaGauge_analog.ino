#include <SPI.h>
#include <mcp_can.h>

const int CAN_CS = 10;
MCP_CAN CAN(CAN_CS);

const uint16_t ID_FUNC_REQ_BASE = 0x740; // + ecuId
const uint16_t ID_FUNC_RES_BASE = 0x770; // + ecuId
const uint8_t ECU_ID = 0; // dest ecu id 0..15

// function 38: setLuaGauge(arg1=float volts, arg2=int16 gaugeId)
static void be_u16(uint8_t *b, uint16_t v){ b[0]=(v>>8)&0xFF; b[1]=v&0xFF; }
static void be_u32(uint8_t *b, uint32_t v){ b[0]=(v>>24)&0xFF; b[1]=(v>>16)&0xFF; b[2]=(v>>8)&0xFF; b[3]=v&0xFF; }

void setup(){
  Serial.begin(115200);
  while(!Serial){}
  if (CAN.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
    CAN.setMode(MCP_NORMAL);
    Serial.println("CAN init ok");
  } else {
    Serial.println("CAN init fail");
    while(1){}
  }
}

void loop(){
  int adc = analogRead(A0);
  float volts = (adc / 1023.0f) * 5.0f; // adjust reference as needed
  int16_t gaugeId = 1; // 1..8

  uint8_t data[8];
  be_u16(&data[0], 38); // function id
  uint32_t bits; memcpy(&bits, &volts, sizeof(bits));
  be_u32(&data[2], bits);
  data[6] = (uint8_t)((gaugeId >> 8) & 0xFF);
  data[7] = (uint8_t)(gaugeId & 0xFF);

  uint16_t id = ID_FUNC_REQ_BASE + (ECU_ID & 0x0F);
  CAN.sendMsgBuf(id, 0, 8, data);

  Serial.print("sent setLuaGauge volts="); Serial.print(volts, 3);
  Serial.print(" id="); Serial.println(gaugeId);
  delay(100);
}
