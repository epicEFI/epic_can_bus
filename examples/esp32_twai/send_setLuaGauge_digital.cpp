#include <Arduino.h>
#include "common.h"

const uint32_t ID_FUNC_REQ_BASE = 0x740; // + ecuId
const uint8_t ECU_ID = 0;
const int PIN_IN = 14;

void setup(){
    pinMode(PIN_IN, INPUT_PULLUP);
    Serial.begin(115200);
    while(!Serial) {}
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(GPIO_NUM_5, GPIO_NUM_4, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    if (twai_driver_install(&g_config, &t_config, &f_config) != ESP_OK) { while(1){} }
    if (twai_start() != ESP_OK) { while(1){} }
}

void loop(){
    bool state = digitalRead(PIN_IN) == LOW;
    float v = state ? 1.0f : 0.0f;
    int16_t gaugeId = 2;

    uint8_t data[8];
    be_u16(&data[0], 38);
    uint32_t bits; memcpy(&bits, &v, sizeof(bits));
    be_u32(&data[2], bits);
    data[6] = (uint8_t)((gaugeId >> 8) & 0xFF);
    data[7] = (uint8_t)(gaugeId & 0xFF);

    uint32_t id = ID_FUNC_REQ_BASE + (ECU_ID & 0x0F);
    (void)twai_send(id, data, 8);

    delay(50);
}
