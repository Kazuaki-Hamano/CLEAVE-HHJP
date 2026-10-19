/* SPDX-License-Identifier: MIT */
#define DT_DRV_COMPAT cleave_behavior_studio_ble_discovery

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/ble.h>
#include <zmk/studio/core.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

/* Serialize start/expiry on the system queue. Stop advertising only: existing
 * HID, split and Studio GATT connections remain intact. */
static void discovery_expire(struct k_work *work) {
    int rc = zmk_ble_set_directed_advertising(false);
    if (rc != 0) {
        LOG_WRN("Studio BLE discovery stop failed: %d", rc);
    }
}
K_WORK_DELAYABLE_DEFINE(discovery_timeout, discovery_expire);

static void discovery_start(struct k_work *work) {
    zmk_studio_core_unlock();
    int rc = zmk_ble_set_directed_advertising(true);
    if (rc != 0) {
        zmk_ble_set_directed_advertising(false);
        k_work_cancel_delayable(&discovery_timeout);
        LOG_WRN("Studio BLE discovery start failed: %d", rc);
        return;
    }
    k_work_reschedule(&discovery_timeout, K_SECONDS(60));
}
K_WORK_DEFINE(discovery_start_work, discovery_start);

static int discovery_pressed(struct zmk_behavior_binding *binding,
                             struct zmk_behavior_binding_event event) {
    k_work_submit(&discovery_start_work);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int discovery_released(struct zmk_behavior_binding *binding,
                              struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api discovery_api = {
    .binding_pressed = discovery_pressed,
    .binding_released = discovery_released,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .get_parameter_metadata = zmk_behavior_get_empty_param_metadata,
#endif
};

BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &discovery_api);
