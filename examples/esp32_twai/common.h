#pragma once
#include <driver/twai.h>
#include <string.h>

static inline void be_u16(uint8_t *b, uint16_t v){ b[0]=(v>>8)&0xFF; b[1]=v&0xFF; }
static inline void be_u32(uint8_t *b, uint32_t v){ b[0]=(v>>24)&0xFF; b[1]=(v>>16)&0xFF; b[2]=(v>>8)&0xFF; b[3]=v&0xFF; }

static inline bool twai_send(uint32_t id, const uint8_t *data, uint8_t dlc){
    twai_message_t msg = {0};
    msg.identifier = id;
    msg.data_length_code = dlc;
    memcpy(msg.data, data, dlc);
    return twai_transmit(&msg, pdMS_TO_TICKS(10)) == ESP_OK;
}

static inline bool twai_recv(uint32_t &id, uint8_t *data, uint8_t &dlc){
    twai_message_t msg = {0};
    if (twai_receive(&msg, pdMS_TO_TICKS(1)) != ESP_OK) return false;
    id = msg.identifier;
    dlc = msg.data_length_code;
    memcpy(data, msg.data, dlc);
    return true;
}
