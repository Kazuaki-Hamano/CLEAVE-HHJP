/* SPDX-License-Identifier: MIT */
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/sys/atomic.h>
#include <hal/nrf_power.h>
#include <zmk/event_manager.h>
#include <zmk/events/split_peripheral_status_changed.h>
#include "charge_status.h"

/* XIAO CHG is open drain, active low. Never drive P0.17 as an output.
 * Pull-up is used only with USB present; without USB leave it floating to
 * avoid feeding the charger from the battery. VBUS works with wall chargers.
 */
static const struct device *const charge_gpio = DEVICE_DT_GET(DT_NODELABEL(gpio0));
static bool gpio_ready;

uint8_t cleave_local_power_state(void) {
    if (!gpio_ready) {
        return CLEAVE_POWER_UNKNOWN;
    }
    bool usb = (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
    if (gpio_pin_configure(charge_gpio, 17, GPIO_INPUT | (usb ? GPIO_PULL_UP : 0)) < 0) {
        return CLEAVE_POWER_UNKNOWN;
    }
    if (!usb) {
        return CLEAVE_POWER_BATTERY;
    }
    /* Let the input settle after enabling its pull-up. */
    k_busy_wait(50);
    int pin = gpio_pin_get_raw(charge_gpio, 17);
    return pin < 0 ? CLEAVE_POWER_UNKNOWN :
           pin == 0 ? CLEAVE_POWER_CHARGING : CLEAVE_POWER_USB_IDLE;
}

#define CHARGE_SERVICE BT_UUID_128_ENCODE(0xb6f4a610, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10)
#define CHARGE_VALUE BT_UUID_128_ENCODE(0xb6f4a611, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10)
static struct bt_uuid_128 charge_uuid = BT_UUID_INIT_128(CHARGE_VALUE);

#if !IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static ssize_t read_charge(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                           void *buf, uint16_t len, uint16_t offset) {
    uint8_t value = cleave_local_power_state();
    return bt_gatt_attr_read(conn, attr, buf, len, offset, &value, sizeof(value));
}
BT_GATT_SERVICE_DEFINE(cleave_charge_service,
    BT_GATT_PRIMARY_SERVICE(BT_UUID_DECLARE_128(CHARGE_SERVICE)),
    BT_GATT_CHARACTERISTIC(&charge_uuid.uuid, BT_GATT_CHRC_READ,
                           BT_GATT_PERM_READ_ENCRYPT, read_charge, NULL, NULL));

uint8_t cleave_remote_power_state(uint16_t *age_seconds) {
    *age_seconds = UINT16_MAX;
    return CLEAVE_POWER_UNKNOWN;
}
#else
static struct k_spinlock remote_lock;
static uint8_t remote_state;
static int64_t remote_updated;
static atomic_t read_pending;
static struct bt_gatt_read_params read_params;

uint8_t cleave_remote_power_state(uint16_t *age_seconds) {
    k_spinlock_key_t key = k_spin_lock(&remote_lock);
    int64_t age = (k_uptime_get() - remote_updated) / 1000;
    uint8_t value = remote_state;
    *age_seconds = value ? MIN(age, UINT16_MAX) : UINT16_MAX;
    /* Never continue showing charging when the peer is no longer readable. */
    if (age > 20) {
        value = CLEAVE_POWER_UNKNOWN;
    }
    k_spin_unlock(&remote_lock, key);
    return value;
}

static uint8_t charge_read_done(struct bt_conn *conn, uint8_t err,
                                struct bt_gatt_read_params *params,
                                const void *data, uint16_t length) {
    ARG_UNUSED(params);
    struct bt_conn_info info;
    if (!err && data && length == 1 &&
        bt_conn_get_info(conn, &info) == 0 && info.state == BT_CONN_CONNECTED &&
        ((const uint8_t *)data)[0] <= CLEAVE_POWER_CHARGING) {
        k_spinlock_key_t key = k_spin_lock(&remote_lock);
        remote_state = ((const uint8_t *)data)[0];
        remote_updated = k_uptime_get();
        k_spin_unlock(&remote_lock, key);
    }
    atomic_clear(&read_pending);
    return BT_GATT_ITER_STOP;
}

static void read_peer(struct bt_conn *conn, void *user_data) {
    ARG_UNUSED(user_data);
    struct bt_conn_info info;
    if (bt_conn_get_info(conn, &info) != 0 || info.role != BT_CONN_ROLE_CENTRAL ||
        info.state != BT_CONN_CONNECTED || !atomic_cas(&read_pending, 0, 1)) {
        return;
    }
    read_params = (struct bt_gatt_read_params){
        .func = charge_read_done, .handle_count = 0,
        .by_uuid = {.start_handle = 1, .end_handle = 0xffff, .uuid = &charge_uuid.uuid}};
    if (bt_gatt_read(conn, &read_params) < 0) {
        atomic_clear(&read_pending);
    }
}

static void poll_charge(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(charge_poll, poll_charge);
static void poll_charge(struct k_work *work) {
    ARG_UNUSED(work);
    bt_conn_foreach(BT_CONN_TYPE_LE, read_peer, NULL);
    k_work_reschedule(&charge_poll, K_SECONDS(5));
}

static int peer_status(const zmk_event_t *event) {
    const struct zmk_split_peripheral_status_changed *status =
        as_zmk_split_peripheral_status_changed(event);
    if (status && !status->connected) {
        k_spinlock_key_t key = k_spin_lock(&remote_lock);
        remote_state = CLEAVE_POWER_UNKNOWN;
        k_spin_unlock(&remote_lock, key);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_charge_status, peer_status);
ZMK_SUBSCRIPTION(cleave_charge_status, zmk_split_peripheral_status_changed);
#endif

static int charge_status_init(void) {
    gpio_ready = device_is_ready(charge_gpio) &&
                 gpio_pin_configure(charge_gpio, 17, GPIO_INPUT) == 0;
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    k_work_schedule(&charge_poll, K_SECONDS(5));
#endif
    return gpio_ready ? 0 : -ENODEV;
}
SYS_INIT(charge_status_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
