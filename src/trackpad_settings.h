/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
#define CLEAVE_TRACKPAD_REPORT_SIZE 32
/* Percent units; maximum is the acceleration multiplier, before base speed. */
struct cleave_trackpad_config {
    uint16_t speed, acceleration, maximum;
    uint8_t sensitivity;
};
int cleave_trackpad_validate(const struct cleave_trackpad_config *cfg);
void cleave_trackpad_get(struct cleave_trackpad_config *cfg, uint32_t *generation);
void cleave_trackpad_report(uint8_t *out);
int cleave_trackpad_command(const uint8_t *data, unsigned len);
