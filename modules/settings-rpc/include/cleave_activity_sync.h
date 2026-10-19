/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
int cleave_activity_store(uint32_t idle_ms, uint32_t sleep_ms);
int cleave_activity_sync_queue(uint32_t idle_ms, uint32_t sleep_ms);
void cleave_activity_sync_ack(uint8_t source, uint32_t transaction_id,
                              uint32_t idle_ms, uint32_t sleep_ms);
