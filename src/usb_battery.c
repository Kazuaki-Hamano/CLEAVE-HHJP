/* SPDX-License-Identifier: MIT */
#include <string.h>
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/usb/class/usb_hid.h>
#include <zmk/battery.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/split_peripheral_status_changed.h>
#include "charge_status.h"
#include "app_update.h"

/* Vendor collection: read-only feature report, independent of keyboard/mouse HID.
 * ID, version, central %, peripheral %, peripheral-valid, age in seconds (LE).
 * A disconnected/unseen peripheral is unknown, never a fictitious zero percent.
 */
static const uint8_t descriptor[] = {
    0x06, 0x60, 0xff, 0x09, 0x01, 0xa1, 0x01, 0x85, 0x01,
    0x09, 0x02, 0x15, 0x00, 0x26, 0xff, 0x00,
    0x75, 0x08, 0x95, 0x06, 0xb1, 0x02,
    /* Feature report 2: version, local state, peer state, peer age (LE). */
    0x85, 0x02, 0x09, 0x03, 0x95, 0x05, 0xb1, 0x02,
    0x85, 0x03, 0x09, 0x04, 0x95, 0x1f, 0xb1, 0x02,
    0x85, 0x04, 0x09, 0x05, 0x95, 0x07, 0xb1, 0x02,
    0x85, 0x05, 0x09, 0x06, 0x95, 0x1f, 0xb1, 0x02,
    /* Read-only cached battery diagnostics; never triggers an ADC sample. */
    0x85, 0x06, 0x09, 0x07, 0x95, 0x0f, 0xb1, 0x02,
    0xc0,
};
static struct k_spinlock state_lock;
static uint8_t right_level;
static bool right_valid;
static int64_t right_updated;
static uint8_t report[7];
static uint8_t power_report[6];
static uint8_t update_report[CLEAVE_UPDATE_INFO_SIZE];
static uint8_t diagnostic_report[16];
static int64_t local_changed;
static bool local_seen;

static void battery_diagnostics(void) {
    memset(diagnostic_report, 0, sizeof(diagnostic_report));
    diagnostic_report[0] = 6;
    diagnostic_report[1] = 1;
    diagnostic_report[2] = zmk_battery_state_of_charge();
    diagnostic_report[3] = cleave_local_power_state();
#if DT_HAS_CHOSEN(zmk_battery)
    const struct device *sensor = DEVICE_DT_GET(DT_CHOSEN(zmk_battery));
#else
    const struct device *sensor = device_get_binding("BATTERY");
#endif
    struct sensor_value value;
    if (sensor && device_is_ready(sensor)) {
        /* The ZMK voltage-divider driver returns its cached sample here.
         * Do not call sensor_sample_fetch: the normal battery worker owns ADC/GPIO. */
        if (sensor_channel_get(sensor, SENSOR_CHAN_GAUGE_VOLTAGE, &value) == 0) {
            int32_t mv = value.val1 * 1000 + value.val2 / 1000;
            if (mv >= 0 && mv <= UINT16_MAX) {
                sys_put_le16(mv, diagnostic_report + 4);
                diagnostic_report[7] |= 1;
            }
        }
        if (sensor_channel_get(sensor, SENSOR_CHAN_GAUGE_STATE_OF_CHARGE, &value) == 0 &&
            value.val1 >= 0 && value.val1 <= 100) {
            diagnostic_report[6] = value.val1;
            diagnostic_report[7] |= 2;
        }
    }
    sys_put_le32((uint32_t)(k_uptime_get() / 1000), diagnostic_report + 8);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    uint32_t age = local_seen ? MIN((k_uptime_get() - local_changed) / 1000, UINT32_MAX)
                             : UINT32_MAX;
    k_spin_unlock(&state_lock, key);
    sys_put_le32(age, diagnostic_report + 12);
}

static int get_report(const struct device *dev, struct usb_setup_packet *setup,
                      int32_t *len, uint8_t **data) {
    ARG_UNUSED(dev);
    if (setup->wValue == 0x0306) {
        battery_diagnostics();
        *data = diagnostic_report;
        *len = sizeof(diagnostic_report);
        return 0;
    }
    if (setup->wValue == 0x0303 || setup->wValue == 0x0305) {
        if (setup->wValue == 0x0303) { cleave_update_local_info(update_report); }
        else { cleave_update_remote_info(update_report); }
        *data = update_report;
        *len = sizeof(update_report);
        return 0;
    }
    if (setup->wValue == 0x0302) {
        uint16_t power_age;
        power_report[0] = 2;
        power_report[1] = 1;
        power_report[2] = cleave_local_power_state();
        power_report[3] = cleave_remote_power_state(&power_age);
        power_report[4] = power_age & 0xff;
        power_report[5] = power_age >> 8;
        *data = power_report;
        *len = sizeof(power_report);
        return 0;
    }
    if (setup->wValue != 0x0301) {
        return -ENOTSUP;
    }
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    uint16_t age = right_valid ? MIN((k_uptime_get() - right_updated) / 1000, 65535) : 65535;
    report[0] = 1;
    report[1] = 1;
    report[2] = zmk_battery_state_of_charge();
    report[3] = right_level;
    report[4] = right_valid;
    report[5] = age & 0xff;
    report[6] = age >> 8;
    k_spin_unlock(&state_lock, key);
    *data = report;
    *len = sizeof(report);
    return 0;
}

static int battery_listener(const zmk_event_t *event) {
    const struct zmk_battery_state_changed *local = as_zmk_battery_state_changed(event);
    const struct zmk_peripheral_battery_state_changed *battery =
        as_zmk_peripheral_battery_state_changed(event);
    const struct zmk_split_peripheral_status_changed *status =
        as_zmk_split_peripheral_status_changed(event);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    if (local) {
        local_changed = k_uptime_get();
        local_seen = true;
    }
    if (battery && battery->source == 0) {
        right_level = battery->state_of_charge;
        right_updated = k_uptime_get();
        right_valid = true;
    } else if (status && !status->connected) {
        right_valid = false;
    }
    k_spin_unlock(&state_lock, key);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_usb_battery, battery_listener);
ZMK_SUBSCRIPTION(cleave_usb_battery, zmk_battery_state_changed);
ZMK_SUBSCRIPTION(cleave_usb_battery, zmk_peripheral_battery_state_changed);
ZMK_SUBSCRIPTION(cleave_usb_battery, zmk_split_peripheral_status_changed);

static int set_report(const struct device *dev, struct usb_setup_packet *setup,
                      int32_t *len, uint8_t **data) {
    ARG_UNUSED(dev);
    if (setup->wValue != 0x0304 || (*len != 8 && *len != 32) || (*data)[0] != 4 || (*data)[1] != 1 ||
        (*data)[2] > 1 || memcmp(*data + 3, "BOOT", 4) != 0 || (*data)[7] != 0) {
        return -EINVAL;
    }
    for (int i = 8; i < *len; i++) {
        if ((*data)[i] != 0) { return -EINVAL; }
    }
    return cleave_update_request((*data)[2]);
}
static const struct hid_ops ops = {.get_report = get_report, .set_report = set_report};
static int battery_usb_init(void) {
    const struct device *dev = device_get_binding("HID_1");
    if (!dev || !device_is_ready(dev)) {
        return -ENODEV;
    }
    usb_hid_register_device(dev, descriptor, sizeof(descriptor), &ops);
    return usb_hid_init(dev);
}
SYS_INIT(battery_usb_init, APPLICATION, CONFIG_ZMK_USB_HID_INIT_PRIORITY);
