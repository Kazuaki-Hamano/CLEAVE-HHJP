/* SPDX-License-Identifier: MIT */
#include <stddef.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/util.h>
#include <zmk/event_manager.h>
#include <zmk/studio/custom.h>
#include <cormoran/zmk/custom_settings.h>
#include "trackpad_settings.h"

/* Generic DYA Settings UI owns all tuning and persistence. No Windows/HID
 * settings or old cleave_trackpad/config records are read by this version. */
static struct zmk_rpc_custom_subsystem_meta trackpad_meta = {
    ZMK_RPC_CUSTOM_SUBSYSTEM_UI_URLS(),
    .security = ZMK_STUDIO_RPC_HANDLER_UNSECURED,
};
static bool settings_only_request(const zmk_custom_CallRequest *req, pb_callback_t *response) {
    ARG_UNUSED(req);
    ARG_UNUSED(response);
    return false; /* Edits use the generic custom-settings RPC. */
}
ZMK_RPC_CUSTOM_SUBSYSTEM(cleave_right_trackpad, &trackpad_meta, settings_only_request);
ZMK_RPC_CUSTOM_SUBSYSTEM(cleave_left_scroll, &trackpad_meta, settings_only_request);

#define TP_INT(name, subsystem, key, initial, lo, hi)                                       \
    BUILD_ASSERT(sizeof("custom_settings/" subsystem "/" key) <= SETTINGS_MAX_NAME_LEN,       \
                 "Trackpad setting storage name exceeds Zephyr settings buffer");           \
    ZMK_CUSTOM_SETTING_DEFINE(name, subsystem, key, ZMK_CUSTOM_SETTING_VALUE_TYPE_INT32,     \
        ZMK_CUSTOM_SETTING_VALUE_INT32(initial),                                           \
        ZMK_CUSTOM_SETTING_CONFIDENTIALITY_RPC_PUBLIC,                                     \
        ZMK_CUSTOM_SETTING_PERMISSION_UNSECURE, ZMK_CUSTOM_SETTING_PERMISSION_UNSECURE,     \
        ZMK_CUSTOM_SETTING_RANGE_INT32(lo, hi))

TP_INT(right_speed, "cleave_right_trackpad", "right_speed_percent", 200, 30, 800);
TP_INT(right_acceleration, "cleave_right_trackpad", "acceleration_percent", 0, 0, 300);
TP_INT(right_maximum, "cleave_right_trackpad", "right_max_gain_percent", 300, 100, 800);
TP_INT(right_native_scroll, "cleave_right_trackpad", "native_scroll_percent", 100, 10, 400);
TP_INT(left_scroll, "cleave_left_scroll", "left_scroll_percent", 100, 10, 400);

static struct k_spinlock config_lock;
static struct cleave_trackpad_config config = {200, 0, 300, 1, 100, 100};
static uint32_t right_generation = 1, left_generation = 1;
struct setting_field {
    const struct zmk_custom_setting *setting;
    size_t offset;
    bool left;
};
static const struct setting_field fields[] = {
    {&right_speed, offsetof(struct cleave_trackpad_config, speed), false},
    {&right_acceleration, offsetof(struct cleave_trackpad_config, acceleration), false},
    {&right_maximum, offsetof(struct cleave_trackpad_config, maximum), false},
    {&right_native_scroll, offsetof(struct cleave_trackpad_config, native_scroll), false},
    {&left_scroll, offsetof(struct cleave_trackpad_config, scroll), true},
};

static void apply_field(const struct setting_field *field) {
    struct zmk_custom_setting_value value;
    if (zmk_custom_setting_read(field->setting, &value) < 0 ||
        value.type != ZMK_CUSTOM_SETTING_VALUE_TYPE_INT32) {
        return;
    }
    /* The registry validates bounds before a write/load becomes observable. */
    k_spinlock_key_t key = k_spin_lock(&config_lock);
    uint16_t *dest = (uint16_t *)((uint8_t *)&config + field->offset);
    if (*dest != value.int32_value) {
        *dest = value.int32_value;
        if (field->left) { left_generation++; } else { right_generation++; }
    }
    k_spin_unlock(&config_lock, key);
}
static int settings_event(const zmk_event_t *event) {
    if (as_zmk_custom_settings_initialized(event)) {
        /* Unlike SYS_INIT, this runs after persisted registry values load. */
        for (size_t i = 0; i < ARRAY_SIZE(fields); i++) { apply_field(&fields[i]); }
    } else {
        const struct zmk_custom_setting_changed *changed = as_zmk_custom_setting_changed(event);
        if (changed) {
            for (size_t i = 0; i < ARRAY_SIZE(fields); i++) {
                if (changed->setting == fields[i].setting) {
                    apply_field(&fields[i]);
                    break;
                }
            }
        }
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_trackpad_settings, settings_event);
ZMK_SUBSCRIPTION(cleave_trackpad_settings, zmk_custom_settings_initialized);
ZMK_SUBSCRIPTION(cleave_trackpad_settings, zmk_custom_setting_changed);

void cleave_trackpad_get(struct cleave_trackpad_config *out, uint32_t *generation) {
    k_spinlock_key_t key = k_spin_lock(&config_lock);
    *out = config;
    if (generation) { *generation = right_generation; }
    k_spin_unlock(&config_lock, key);
}
void cleave_trackpad_get_scroll(struct cleave_trackpad_config *out, uint32_t *generation) {
    k_spinlock_key_t key = k_spin_lock(&config_lock);
    *out = config;
    if (generation) { *generation = left_generation; }
    k_spin_unlock(&config_lock, key);
}
