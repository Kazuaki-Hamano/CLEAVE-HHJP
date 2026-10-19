/* SPDX-License-Identifier: MIT */
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
#include <dt-bindings/zmk/keys.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/events/layer_state_changed.h>
#include "trackpad_navigation.h"

static atomic_t pending_key;
static int layer_changed(const zmk_event_t *event) {
    const struct zmk_layer_state_changed *layer = as_zmk_layer_state_changed(event);
    if (layer && layer->layer == 1) { cleave_trackpad_reset_local(); }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(trackpad_navigation_layer, layer_changed);
ZMK_SUBSCRIPTION(trackpad_navigation_layer, zmk_layer_state_changed);
static void release_key(struct k_work *work) {
    ARG_UNUSED(work);
    raise_zmk_keycode_state_changed_from_encoded(atomic_get(&pending_key), false, k_uptime_get());
    atomic_clear(&pending_key);
}
K_WORK_DELAYABLE_DEFINE(release_work, release_key);
static void press_key(struct k_work *work) {
    ARG_UNUSED(work);
    raise_zmk_keycode_state_changed_from_encoded(atomic_get(&pending_key), true, k_uptime_get());
    k_work_reschedule(&release_work, K_MSEC(30));
}
K_WORK_DEFINE(press_work, press_key);
void cleave_trackpad_navigate(bool forward) {
    uint32_t key = forward ? C_AC_FORWARD : C_AC_BACK;
    if (atomic_cas(&pending_key, 0, key)) { k_work_submit(&press_work); }
}
