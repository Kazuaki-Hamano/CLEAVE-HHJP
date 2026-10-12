/* SPDX-License-Identifier: MIT */
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/usb/class/usb_hid.h>
#include <zmk/battery.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/split_peripheral_status_changed.h>

/* Vendor collection: read-only feature report, independent of keyboard/mouse HID.
 * ID, version, central %, peripheral %, peripheral-valid, age in seconds (LE).
 * A disconnected/unseen peripheral is unknown, never a fictitious zero percent.
 */
static const uint8_t descriptor[] = {
    0x06, 0x60, 0xff, 0x09, 0x01, 0xa1, 0x01, 0x85, 0x01,
    0x09, 0x02, 0x15, 0x00, 0x26, 0xff, 0x00,
    0x75, 0x08, 0x95, 0x06, 0xb1, 0x02, 0xc0,
};
static struct k_spinlock state_lock;
static uint8_t right_level;
static bool right_valid;
static int64_t right_updated;
static uint8_t report[7];

static int get_report(const struct device *dev, struct usb_setup_packet *setup,
                      int32_t *len, uint8_t **data) {
    ARG_UNUSED(dev);
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
    const struct zmk_peripheral_battery_state_changed *battery =
        as_zmk_peripheral_battery_state_changed(event);
    const struct zmk_split_peripheral_status_changed *status =
        as_zmk_split_peripheral_status_changed(event);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
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
ZMK_SUBSCRIPTION(cleave_usb_battery, zmk_peripheral_battery_state_changed);
ZMK_SUBSCRIPTION(cleave_usb_battery, zmk_split_peripheral_status_changed);

static const struct hid_ops ops = {.get_report = get_report};
static int battery_usb_init(void) {
    const struct device *dev = device_get_binding("HID_1");
    if (!dev || !device_is_ready(dev)) {
        return -ENODEV;
    }
    usb_hid_register_device(dev, descriptor, sizeof(descriptor), &ops);
    return usb_hid_init(dev);
}
SYS_INIT(battery_usb_init, APPLICATION, CONFIG_ZMK_USB_HID_INIT_PRIORITY);
