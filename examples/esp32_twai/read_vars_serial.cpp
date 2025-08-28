#include <Arduino.h>
#include "common.h"

const uint32_t ID_GET_VAR_REQ_BASE = 0x700; // + ecuId
const uint32_t ID_GET_VAR_RES_BASE = 0x720; // + ecuId

const int32_t VARS[] = {
    1699696209,   // RPMValue
    1272048601,   // TPSValue
    -1093429509,  // AFRValue
    493641747,    // baseIgnitionAdvance
    681043126     // actualLastInjection
};

uint8_t DEST_ECU = 0; // broadcast
uint8_t SRC_ID = 2;

bool requestVar(int32_t hash){
    uint8_t data[8];
    be_u32(&data[0], (uint32_t)hash);
    uint32_t id = ID_GET_VAR_REQ_BASE + (DEST_ECU & 0x0F);
    return twai_send(id, data, 4);
}

bool readVarResponse(int32_t &outHash, float &outVal){
    uint32_t id; uint8_t len; uint8_t buf[8];
    if (!twai_recv(id, buf, len)) return false;
    if ((id & 0x7F0) != ID_GET_VAR_RES_BASE || len != 8) return false;
    int32_t h = (int32_t)((uint32_t)buf[0]<<24 | (uint32_t)buf[1]<<16 | (uint32_t)buf[2]<<8 | (uint32_t)buf[3]);
    uint32_t bits = (uint32_t)buf[4]<<24 | (uint32_t)buf[5]<<16 | (uint32_t)buf[6]<<8 | (uint32_t)buf[7];
    float v; memcpy(&v, &bits, sizeof(v));
    outHash = h; outVal = v;
    return true;
}

void setup(){
    Serial.begin(115200);
    while(!Serial) {}

    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(GPIO_NUM_5, GPIO_NUM_4, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    if (twai_driver_install(&g_config, &t_config, &f_config) != ESP_OK) {
        Serial.println("TWAI install failed"); while(1){}
    }
    if (twai_start() != ESP_OK) { Serial.println("TWAI start failed"); while(1){} }
}

void loop(){
    for (unsigned i=0;i<sizeof(VARS)/sizeof(VARS[0]);i++){
        (void)requestVar(VARS[i]);
    }
    unsigned long t0 = millis();
    while (millis() - t0 < 50){
        int32_t h; float v;
        if (readVarResponse(h, v)){
            Serial.print("hash="); Serial.print(h);
            Serial.print(" val="); Serial.println(v, 6);
        }
    }
}
