#include <SPI.h>
#include <mcp_can.h>

const int CAN_CS = 10;
const int PWM_PIN = 5; // PWM-capable pin
MCP_CAN CAN(CAN_CS);

const uint16_t ID_GET_VAR_REQ_BASE = 0x700; // + ecuId
const uint16_t ID_GET_VAR_RES_BASE = 0x720; // + ecuId

static void be_u32(uint8_t *b, uint32_t v){ b[0]=(v>>24)&0xFF; b[1]=(v>>16)&0xFF; b[2]=(v>>8)&0xFF; b[3]=v&0xFF; }

// hash for boostOutput
const int32_t HASH_boostOutput = 1239062717;
const uint8_t DEST_ECU = 0;
const uint8_t SRC_ID = 1;

bool requestVar(int32_t hash){
  uint8_t data[8];
  be_u32(&data[0], (uint32_t)hash);
  uint16_t id = ID_GET_VAR_REQ_BASE + (DEST_ECU & 0x0F);
  return CAN.sendMsgBuf(id, 0, 4, data) == CAN_OK;
}

bool readVarResponse(int32_t &outHash, float &outVal){
  unsigned long id = 0; uint8_t len = 0; uint8_t buf[8];
  if (CAN.checkReceive() != CAN_MSGAVAIL) return false;
  if (CAN.readMsgBuf(&id, &len, buf) != CAN_OK) return false;
  if ((id & 0x7F0) != ID_GET_VAR_RES_BASE || len != 8) return false;
  int32_t h = (int32_t)((uint32_t)buf[0]<<24 | (uint32_t)buf[1]<<16 | (uint32_t)buf[2]<<8 | (uint32_t)buf[3]);
  uint32_t bits = (uint32_t)buf[4]<<24 | (uint32_t)buf[5]<<16 | (uint32_t)buf[6]<<8 | (uint32_t)buf[7];
  float v; memcpy(&v, &bits, sizeof(v));
  outHash = h; outVal = v;
  return true;
}

void setup(){
  pinMode(PWM_PIN, OUTPUT);
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
  (void)requestVar(HASH_boostOutput);
  unsigned long t0 = millis();
  while (millis() - t0 < 20){
    int32_t h; float v;
    if (readVarResponse(h, v) && h == HASH_boostOutput){
      // v is duty 0..100 (percent). Map to 0..255
      int duty = constrain((int)(v * 2.55f), 0, 255);
      analogWrite(PWM_PIN, duty);
      Serial.print("boostOutput="); Serial.print(v, 2);
      Serial.print(" duty="); Serial.println(duty);
      break;
    }
  }
  delay(20);
}
