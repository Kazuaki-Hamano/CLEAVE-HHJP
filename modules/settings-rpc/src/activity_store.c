/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <zephyr/settings/settings.h>
#include <zmk/activity.h>
#include <cleave_activity_sync.h>

int cleave_activity_store(uint32_t idle_ms, uint32_t sleep_ms) {
    if (zmk_activity_get_idle_ms() != idle_ms && !zmk_activity_set_idle_ms(idle_ms)) {
        return -ENOTSUP;
    }
    if (zmk_activity_get_sleep_ms() != sleep_ms && !zmk_activity_set_sleep_ms(sleep_ms)) {
        return -ENOTSUP;
    }
    /* Pinned ZMK e5c9b691 activity/s ABI: sleep then idle, both uint32_t.
     * Save synchronously before acknowledgement; the core's delayed duplicate
     * remains harmless (NVS suppresses writes of identical data). */
    const uint32_t values[] = {sleep_ms, idle_ms};
    return settings_save_one("activity/s", values, sizeof(values));
}
