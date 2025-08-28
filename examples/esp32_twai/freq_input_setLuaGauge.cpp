#include <Arduino.h>
#include "common.h"

const uint32_t ID_FUNC_REQ_BASE = 0x740; // + ecuId
const uint8_t ECU_ID = 0;
const int PIN_FREQ = 27;

volatile uint32_t pulseCount = 0;
unsigned long lastMs = 0;

void IRAM_ATTR isrRise(){
    pulseCount++;
}

void setup(){
    pinMode(PIN_FREQ, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_FREQ), isrRise, RISING);

    Serial.begin(115200);
    while(!Serial) {}
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(GPIO_NUM_5, GPIO_NUM_4, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    if (twai_driver_install(&g_config, &t_config, &f_config) != ESP_OK) { while(1){} }
    if (twai_start() != ESP_OK) { while(1){} }
    lastMs = millis();
}

void loop(){
    unsigned long now = millis();
    if (now - lastMs >= 100){
        noInterrupts();
        uint32_t cnt = pulseCount; pulseCount = 0;
        interrupts();
        float hz = (float)cnt * 10.0f; // 100 ms window -> multiply by 10
        int16_t gaugeId = 3;

        uint8_t data[8];
        be_u16(&data[0], 38);
        uint32_t bits; memcpy(&bits, &hz, sizeof(bits));
        be_u32(&data[2], bits);
        data[6] = (uint8_t)((gaugeId >> 8) & 0xFF);
        data[7] = (uint8_t)(gaugeId & 0xFF);

        uint32_t id = ID_FUNC_REQ_BASE + (ECU_ID & 0x0F);
        (void)twai_send(id, data, 8);
        lastMs = now;
    }
}
