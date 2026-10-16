/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>

enum cleave_power_state {
    CLEAVE_POWER_UNKNOWN = 0,
    CLEAVE_POWER_BATTERY = 1,
    CLEAVE_POWER_USB_IDLE = 2,
    CLEAVE_POWER_CHARGING = 3,
};
uint8_t cleave_local_power_state(void);
uint8_t cleave_remote_power_state(uint16_t *age_seconds);
