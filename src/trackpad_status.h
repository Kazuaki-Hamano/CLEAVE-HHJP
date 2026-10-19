/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
#include <stdbool.h>
#define CLEAVE_TRACKPAD_STATUS_CODE 0xc1e0
/* Private MSC event on input-split 0, never a mouse axis/button or sync. */
static inline int32_t cleave_trackpad_status_encode(uint8_t applied, int8_t error) {
    return 0x54500000u | ((uint32_t)(uint8_t)error << 8) | applied;
}
static inline bool cleave_trackpad_status_decode(int32_t value, uint8_t *applied,
                                                 int8_t *error) {
    if (((uint32_t)value & 0xffff0000u) != 0x54500000u ||
        ((uint32_t)value & 0xffu) > 4) { return false; }
    *applied = (uint8_t)value;
    *error = (int8_t)((uint32_t)value >> 8);
    return true;
}
