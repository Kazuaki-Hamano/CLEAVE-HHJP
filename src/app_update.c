/* SPDX-License-Identifier: MIT */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/sys/reboot.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <hal/nrf_power.h>
#include <dt-bindings/zmk/reset.h>
#include <zmk/event_manager.h>
#include <zmk/events/split_peripheral_status_changed.h>
#include <zmk/split/central.h>
#include "app_update.h"

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#define UPDATE_SIDE 0
#define UPDATE_SIDE_NAME "LEFT"
#else
#define UPDATE_SIDE 1
#define UPDATE_SIDE_NAME "RIGHT"
#endif
/* Retained by the GATT/HID info response; also identifies the UF2 image itself. */
static const char image_identity[] = "CLEAVE_HHJP_UPDATE1|" UPDATE_SIDE_NAME "|" CLEAVE_UPDATE_BUILD_ID;
void cleave_update_local_info(uint8_t *out) {
    memset(out, 0, CLEAVE_UPDATE_INFO_SIZE);
    out[0] = 3; out[1] = 1; out[2] = UPDATE_SIDE;
    out[3] = 1 | ((NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) ? 2 : 0);
    memcpy(out + 4, image_identity + sizeof(image_identity) - 9, 8);
    memcpy(out + 12, "CHHP", 4);
    uint32_t uid[2] = {NRF_FICR->DEVICEID[0], NRF_FICR->DEVICEID[1]};
    memcpy(out + 16, uid, sizeof(uid));
}

static struct bt_uuid_128 info_uuid = BT_UUID_INIT_128(
    BT_UUID_128_ENCODE(0xb6f4a621, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10));
static ssize_t info_read(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                         void *buf, uint16_t len, uint16_t offset) {
    uint8_t value[CLEAVE_UPDATE_INFO_SIZE];
    cleave_update_local_info(value);
    /* Fits even the default ATT MTU (23), without negotiating a larger MTU. */
    return bt_gatt_attr_read(conn, attr, buf, len, offset, value, 16);
}
BT_GATT_SERVICE_DEFINE(cleave_update_info_service,
    BT_GATT_PRIMARY_SERVICE(BT_UUID_DECLARE_128(
        BT_UUID_128_ENCODE(0xb6f4a620, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10))),
    BT_GATT_CHARACTERISTIC(&info_uuid.uuid, BT_GATT_CHRC_READ,
        BT_GATT_PERM_READ_ENCRYPT, info_read, NULL, NULL));

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static struct k_spinlock info_lock;
static uint8_t remote_info[CLEAVE_UPDATE_INFO_SIZE];
static int64_t remote_updated;
static atomic_t pending;
static struct bt_gatt_read_params read_params;
static uint8_t read_buffer[16];
static size_t read_size;

void cleave_update_remote_info(uint8_t *out) {
    k_spinlock_key_t key = k_spin_lock(&info_lock);
    if (remote_info[3] && k_uptime_get() - remote_updated <= 20000) {
        memcpy(out, remote_info, CLEAVE_UPDATE_INFO_SIZE);
    } else {
        memset(out, 0, CLEAVE_UPDATE_INFO_SIZE);
        out[1] = 1; out[2] = 1;
    }
    out[0] = 5;
    k_spin_unlock(&info_lock, key);
}

static uint8_t info_done(struct bt_conn *conn, uint8_t err,
                         struct bt_gatt_read_params *params, const void *data, uint16_t len) {
    ARG_UNUSED(params);
    if (!err && data && read_size + len <= sizeof(read_buffer)) {
        memcpy(read_buffer + read_size, data, len);
        read_size += len;
        if (read_size < sizeof(read_buffer)) {
            return BT_GATT_ITER_CONTINUE;
        }
        struct bt_conn_info info;
        if (read_buffer[0] == 3 && read_buffer[1] == 1 && read_buffer[2] == 1 &&
            memcmp(read_buffer + 12, "CHHP", 4) == 0 &&
            bt_conn_get_info(conn, &info) == 0 && info.state == BT_CONN_STATE_CONNECTED) {
            k_spinlock_key_t key = k_spin_lock(&info_lock);
            memset(remote_info, 0, sizeof(remote_info));
            memcpy(remote_info, read_buffer, sizeof(read_buffer));
            remote_updated = k_uptime_get();
            k_spin_unlock(&info_lock, key);
        }
    }
    atomic_clear(&pending);
    return BT_GATT_ITER_STOP;
}
static void read_info_peer(struct bt_conn *conn, void *user_data) {
    ARG_UNUSED(user_data);
    struct bt_conn_info info;
    if (bt_conn_get_info(conn, &info) != 0 || info.role != BT_CONN_ROLE_CENTRAL ||
        info.state != BT_CONN_STATE_CONNECTED || !atomic_cas(&pending, 0, 1)) {
        return;
    }
    read_size = 0;
    read_params = (struct bt_gatt_read_params){.func = info_done, .handle_count = 0,
        .by_uuid = {.start_handle = 1, .end_handle = 0xffff, .uuid = &info_uuid.uuid}};
    if (bt_gatt_read(conn, &read_params) < 0) {
        atomic_clear(&pending);
    }
}
static void poll_info(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(info_poll, poll_info);
static void poll_info(struct k_work *work) {
    ARG_UNUSED(work);
    bt_conn_foreach(BT_CONN_TYPE_LE, read_info_peer, NULL);
    k_work_reschedule(&info_poll, K_SECONDS(5));
}
static int info_status(const zmk_event_t *event) {
    const struct zmk_split_peripheral_status_changed *status =
        as_zmk_split_peripheral_status_changed(event);
    if (status && !status->connected) {
        k_spinlock_key_t key = k_spin_lock(&info_lock);
        memset(remote_info, 0, sizeof(remote_info));
        k_spin_unlock(&info_lock, key);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_update_info, info_status);
ZMK_SUBSCRIPTION(cleave_update_info, zmk_split_peripheral_status_changed);
static int update_info_init(void) {
    k_work_schedule(&info_poll, K_SECONDS(6));
    return 0;
}
SYS_INIT(update_info_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);

static atomic_t boot_pending;
static uint8_t requested_side;
static void enter_boot(struct k_work *work) {
    ARG_UNUSED(work);
    if (requested_side == 0) {
        sys_reboot(RST_UF2);
    } else {
        struct zmk_behavior_binding binding = {.behavior_dev = "bootload"};
        struct zmk_behavior_binding_event event = {
            .source = 0, .position = 48, .timestamp = k_uptime_get()};
        zmk_split_central_invoke_behavior(0, &binding, event, true);
    }
    atomic_clear(&boot_pending);
}
K_WORK_DELAYABLE_DEFINE(boot_work, enter_boot);
int cleave_update_request(uint8_t side) {
    if (side > 1) { return -EINVAL; }
    if (side == 1) {
        uint8_t peer[CLEAVE_UPDATE_INFO_SIZE];
        cleave_update_remote_info(peer);
        /* Only boot a peripheral that has update support and USB power. */
        if ((peer[3] & 3) != 3) { return -ENODEV; }
    }
    if (!atomic_cas(&boot_pending, 0, 1)) { return -EBUSY; }
    requested_side = side;
    /* Finish the USB control transfer before either side leaves normal mode. */
    k_work_schedule(&boot_work, K_MSEC(250));
    return 0;
}
#else
void cleave_update_remote_info(uint8_t *out) { memset(out, 0, CLEAVE_UPDATE_INFO_SIZE); }
int cleave_update_request(uint8_t side) { ARG_UNUSED(side); return -ENOTSUP; }
#endif
