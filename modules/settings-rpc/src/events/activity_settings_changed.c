/*
 * Copyright (c) 2026 The ZMK Contributors
 *
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/logging/log.h>
#include <zmk/activity.h>
#include <cleave_activity_sync.h>
#include <zmk/events/activity_settings_report.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_settings_changed.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

ZMK_EVENT_IMPL(zmk_activity_settings_changed);

/**
 * Event listener to apply activity settings when relay event is received
 */
static int activity_settings_changed_listener(const zmk_event_t *eh) {
    struct zmk_activity_settings_changed *ev =
        as_zmk_activity_settings_changed(eh);
    if (!ev) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    // Only apply settings from relayed events (not self-originated)
    if (ev->source != ZMK_RELAY_EVENT_SOURCE_SELF) {
        LOG_DBG(
            "Applying relayed activity settings: idle=%d ms, sleep=%d ms from "
            "source %d",
            ev->idle_ms, ev->sleep_ms, ev->source);

        int ret = cleave_activity_store(ev->idle_ms, ev->sleep_ms);
        if (ret == 0 && ev->transaction_id != 0) {
            struct zmk_activity_settings_report report = {
                .transaction_id = ev->transaction_id,
                .idle_ms = zmk_activity_get_idle_ms(),
                .sleep_ms = zmk_activity_get_sleep_ms(),
                .source = ZMK_RELAY_EVENT_SOURCE_SELF,
            };
            raise_zmk_activity_settings_report(report);
        } else if (ret < 0) {
            LOG_WRN("Activity sync save failed: %d", ret);
        }
    }

    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(activity_settings_apply, activity_settings_changed_listener);
ZMK_SUBSCRIPTION(activity_settings_apply, zmk_activity_settings_changed);

#if IS_ENABLED(CONFIG_ZMK_SPLIT_RELAY_EVENT)

ZMK_RELAY_EVENT_HANDLE(zmk_activity_settings_changed, as, source);

#endif  // IS_ENABLED(CONFIG_ZMK_SPLIT_RELAY_EVENT)