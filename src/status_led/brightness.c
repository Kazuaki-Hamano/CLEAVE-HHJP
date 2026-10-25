/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/atomic.h>
#include <zmk/event_manager.h>
#include <zmk/events/split_peripheral_status_changed.h>
#include <zmk/split/bluetooth/peripheral.h>
#include <cormoran/zmk/custom_settings.h>
#include "brightness.h"
#include "../peer_work.h"
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#include <zmk/studio/custom.h>
#include <cleave_split_status.h>
#endif

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

/* Live and saved values travel together. Preview never writes peripheral flash;
 * reconnect/boot always reasserts the central's authoritative saved value.
 * ACK is sent only after the right has saved and applied the pair. */
enum led_config_kind { LED_REQUEST, LED_UPDATE, LED_ACK };
struct zmk_led_config {
    uint32_t sequence;
    uint8_t live, saved, kind, source;
};
ZMK_EVENT_DECLARE(zmk_led_config);
ZMK_EVENT_IMPL(zmk_led_config);
ZMK_RELAY_EVENT_HANDLE(zmk_led_config, lc, source);

static atomic_t brightness = 100;
uint8_t cleave_led_brightness_get(void) { return atomic_get(&brightness); }
static void apply_live(uint8_t value) {
    atomic_set(&brightness, value);
    cleave_led_refresh();
}
static bool valid_pair(const struct zmk_led_config *ev) {
    return ev->live <= 100 && ev->saved <= 100;
}
static struct zmk_led_config state = {.live = 100, .saved = 100};
static bool ready, pending;
K_MUTEX_DEFINE(led_config_lock);
static void led_sync_work(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(led_work, led_sync_work);
static void schedule_led_sync(int delay_ms) {
    k_work_reschedule_for_queue(&cleave_peer_work_q, &led_work, K_MSEC(delay_ms));
}

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static struct zmk_rpc_custom_subsystem_meta led_meta = {
    ZMK_RPC_CUSTOM_SUBSYSTEM_UI_URLS(),
    .security = ZMK_STUDIO_RPC_HANDLER_UNSECURED,
};
static bool settings_only_request(const zmk_custom_CallRequest *req, pb_callback_t *response) {
    ARG_UNUSED(req); ARG_UNUSED(response); return false;
}
ZMK_RPC_CUSTOM_SUBSYSTEM(cleave_led, &led_meta, settings_only_request);
BUILD_ASSERT(sizeof("custom_settings/cleave_led/brightness_percent") <= SETTINGS_MAX_NAME_LEN,
             "LED setting name exceeds storage limit");
ZMK_CUSTOM_SETTING_DEFINE(awake_brightness, "cleave_led", "brightness_percent",
    ZMK_CUSTOM_SETTING_VALUE_TYPE_INT32, ZMK_CUSTOM_SETTING_VALUE_INT32(100),
    ZMK_CUSTOM_SETTING_CONFIDENTIALITY_RPC_PUBLIC,
    ZMK_CUSTOM_SETTING_PERMISSION_UNSECURE, ZMK_CUSTOM_SETTING_PERMISSION_UNSECURE,
    ZMK_CUSTOM_SETTING_RANGE_INT32(0, 100));

static int led_registry_event(const zmk_event_t *event) {
    const struct zmk_custom_setting_changed *changed = as_zmk_custom_setting_changed(event);
    bool init = as_zmk_custom_settings_initialized(event) != NULL;
    if (!init && (!changed || changed->setting != &awake_brightness)) {
        return ZMK_EV_EVENT_BUBBLE;
    }
    struct zmk_custom_setting_value value;
    if (zmk_custom_setting_read(&awake_brightness, &value) < 0 ||
        value.type != ZMK_CUSTOM_SETTING_VALUE_TYPE_INT32 ||
        value.int32_value < 0 || value.int32_value > 100) { return ZMK_EV_EVENT_BUBBLE; }
    k_mutex_lock(&led_config_lock, K_FOREVER);
    ready = true;
    state.live = value.int32_value;
    if (init || changed->kind == ZMK_CUSTOM_SETTING_CHANGED_SAVED ||
        changed->kind == ZMK_CUSTOM_SETTING_CHANGED_RESET) {
        state.saved = value.int32_value;
    }
    state.sequence++;
    pending = true;
    k_mutex_unlock(&led_config_lock);
    apply_live(value.int32_value);
    schedule_led_sync(0);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_led_settings, led_registry_event);
ZMK_SUBSCRIPTION(cleave_led_settings, zmk_custom_settings_initialized);
ZMK_SUBSCRIPTION(cleave_led_settings, zmk_custom_setting_changed);
#else
/* The right keeps a separate fallback so it boots with the saved brightness
 * even before the left is available. Live previews never touch this record. */
static int32_t stored_brightness = 100;
static int led_load(const char *name, size_t len, settings_read_cb cb, void *arg) {
    if (strcmp(name, "saved")) { return -ENOENT; }
    int32_t value;
    if (len != sizeof(value)) { return -EINVAL; }
    int ret = cb(arg, &value, sizeof(value));
    if (ret != sizeof(value)) { return ret < 0 ? ret : -EINVAL; }
    if (value < 0 || value > 100) { return -EINVAL; }
    stored_brightness = value;
    return 0;
}
SETTINGS_STATIC_HANDLER_DEFINE(cleave_led_saved, "cleave_led", NULL, led_load, NULL, NULL);
static int led_peripheral_init(const zmk_event_t *event) {
    k_mutex_lock(&led_config_lock, K_FOREVER);
    ready = true;
    state.live = state.saved = stored_brightness;
    pending = true; /* Ask central for its current live/saved pair. */
    state.kind = LED_REQUEST;
    k_mutex_unlock(&led_config_lock);
    apply_live(stored_brightness);
    schedule_led_sync(0);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_led_peripheral_init, led_peripheral_init);
ZMK_SUBSCRIPTION(cleave_led_peripheral_init, zmk_custom_settings_initialized);
static int led_connection_event(const zmk_event_t *event) {
    k_mutex_lock(&led_config_lock, K_FOREVER);
    if (ready) { state.kind = LED_REQUEST; pending = true; schedule_led_sync(0); }
    k_mutex_unlock(&led_config_lock);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_led_connection, led_connection_event);
ZMK_SUBSCRIPTION(cleave_led_connection, zmk_split_peripheral_status_changed);
#endif

static int led_config_event(const zmk_event_t *event) {
    const struct zmk_led_config *ev = as_zmk_led_config(event);
    if (!ev || ev->source == ZMK_RELAY_EVENT_SOURCE_SELF) { return ZMK_EV_EVENT_BUBBLE; }
    k_mutex_lock(&led_config_lock, K_FOREVER);
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    if (ready && ev->source == 1) {
        if (ev->kind == LED_REQUEST) { pending = true; schedule_led_sync(0); }
        if (ev->kind == LED_ACK && valid_pair(ev) && ev->sequence == state.sequence &&
            ev->live == state.live && ev->saved == state.saved) {
            pending = false;
            k_work_cancel_delayable(&led_work);
        }
    }
#else
    if (ready && ev->source == 0 && ev->kind == LED_UPDATE && valid_pair(ev)) {
        state = *ev;
        pending = true;
        schedule_led_sync(0);
    }
#endif
    k_mutex_unlock(&led_config_lock);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_led_config, led_config_event);
ZMK_SUBSCRIPTION(cleave_led_config, zmk_led_config);

static void led_sync_work(struct k_work *work) {
    k_mutex_lock(&led_config_lock, K_FOREVER);
    if (!ready || !pending) { k_mutex_unlock(&led_config_lock); return; }
    struct zmk_led_config snapshot = state;
    struct zmk_led_config packet = snapshot;
    k_mutex_unlock(&led_config_lock);
    packet.source = ZMK_RELAY_EVENT_SOURCE_SELF;
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    if (cleave_split_peripheral_connected()) {
        packet.kind = LED_UPDATE;
        raise_zmk_led_config(packet);
    }
#else
    if (packet.kind == LED_REQUEST) {
        if (zmk_split_bt_peripheral_is_connected()) { raise_zmk_led_config(packet); }
    } else {
        apply_live(packet.live);
        int32_t saved = packet.saved;
        int ret = 0;
        if (saved != stored_brightness) {
            ret = settings_save_one("cleave_led/saved", &saved, sizeof(saved));
            if (ret == 0) { stored_brightness = saved; }
        }
        if (ret == 0) {
            packet.kind = LED_ACK;
            raise_zmk_led_config(packet);
            k_mutex_lock(&led_config_lock, K_FOREVER);
            if (state.kind == LED_UPDATE && state.sequence == packet.sequence &&
                state.live == packet.live && state.saved == packet.saved) { pending = false; }
            k_mutex_unlock(&led_config_lock);
        }
    }
#endif
    k_mutex_lock(&led_config_lock, K_FOREVER);
    if (pending) {
        bool newer = state.sequence != snapshot.sequence || state.live != snapshot.live ||
                     state.saved != snapshot.saved || state.kind != snapshot.kind;
        schedule_led_sync(newer ? 0 : 5000);
    }
    k_mutex_unlock(&led_config_lock);
}
