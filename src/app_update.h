/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
#define CLEAVE_UPDATE_INFO_SIZE 32
void cleave_update_local_info(uint8_t *out);
void cleave_update_remote_info(uint8_t *out);
int cleave_update_request(uint8_t side);
