/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
/* Right pointer tuning and left scroll tuning are independent. Sensitivity
 * remains fixed at 1x in each ASIC; all runtime processors run on the central. */
struct cleave_trackpad_config {
    uint16_t speed, acceleration, maximum;
    uint8_t sensitivity;
    uint16_t scroll, native_scroll;
};
/* Right and left generations are independent, including fractional state. */
void cleave_trackpad_get(struct cleave_trackpad_config *cfg, uint32_t *generation);
void cleave_trackpad_get_scroll(struct cleave_trackpad_config *cfg, uint32_t *generation);
