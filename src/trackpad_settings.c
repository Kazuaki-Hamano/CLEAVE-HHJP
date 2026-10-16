/* SPDX-License-Identifier: MIT */
#include <string.h>
#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include "trackpad_settings.h"
#include "peer_work.h"

#define TP_SERVICE BT_UUID_128_ENCODE(0xb6f4a630, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10)
#define TP_VALUE BT_UUID_128_ENCODE(0xb6f4a631, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10)
static struct bt_uuid_128 value_uuid = BT_UUID_INIT_128(TP_VALUE);
static struct k_spinlock cfg_lock;
static struct cleave_trackpad_config config = {200, 0, 300, 1};
static uint32_t generation = 1;
/* Diagnostic fields are exported in previously reserved bytes of Report 7. */
static atomic_t transport_stage;
static atomic_t transport_security;
static atomic_t transport_submit_error;
static atomic_t transport_att_error;
static atomic_t transport_length;
static atomic_t transport_attempts;
static atomic_t transport_completions;
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static struct cleave_trackpad_config saved = {200, 0, 300, 1};
static uint8_t peer_sensitivity;
static int8_t peer_error;
static int64_t peer_updated;
static atomic_t save_pending;
static int8_t save_error;
#endif

int cleave_trackpad_validate(const struct cleave_trackpad_config *c) {
    return c->speed >= 25 && c->speed <= 800 && c->acceleration <= 300 &&
           c->maximum >= 100 && c->maximum <= 800 &&
           c->sensitivity >= 1 && c->sensitivity <= 4 ? 0 : -EINVAL;
}
void cleave_trackpad_get(struct cleave_trackpad_config *out, uint32_t *gen) {
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    *out = config;
    if (gen) { *gen = generation; }
    k_spin_unlock(&cfg_lock, key);
}

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static bool equal_config(const struct cleave_trackpad_config *a,
                         const struct cleave_trackpad_config *b) {
    return a->speed == b->speed && a->acceleration == b->acceleration &&
           a->maximum == b->maximum && a->sensitivity == b->sensitivity;
}
static void encode_config(uint8_t *buf, const struct cleave_trackpad_config *c) {
    sys_put_le16(c->speed, buf);
    sys_put_le16(c->acceleration, buf + 2);
    sys_put_le16(c->maximum, buf + 4);
    buf[6] = c->sensitivity;
}
static struct cleave_trackpad_config decode_config(const uint8_t *buf) {
    return (struct cleave_trackpad_config){sys_get_le16(buf), sys_get_le16(buf + 2),
                                         sys_get_le16(buf + 4), buf[6]};
}
static int settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    if (strcmp(name, "config")) { return -ENOENT; }
    uint8_t buf[8];
    if (len != sizeof(buf)) { return -EINVAL; }
    int n = read_cb(cb_arg, buf, sizeof(buf));
    if (n != sizeof(buf) || buf[0] != 1) { return -EINVAL; }
    struct cleave_trackpad_config c = decode_config(buf + 1);
    if (cleave_trackpad_validate(&c)) { return -EINVAL; }
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    config = saved = c;
    generation++;
    k_spin_unlock(&cfg_lock, key);
    return 0;
}
SETTINGS_STATIC_HANDLER_DEFINE(cleave_trackpad, "cleave_trackpad", NULL, settings_set,
                               NULL, NULL);
static struct cleave_trackpad_config save_snapshot;
static void save_config(struct k_work *work) {
    ARG_UNUSED(work);
    uint8_t buf[8] = {1};
    encode_config(buf + 1, &save_snapshot);
    int err = settings_save_one("cleave_trackpad/config", buf, sizeof(buf));
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    save_error = err ? -1 : 0;
    if (!err) { saved = save_snapshot; }
    k_spin_unlock(&cfg_lock, key);
    atomic_clear(&save_pending);
}
K_WORK_DEFINE(save_work, save_config);

int cleave_trackpad_command(const uint8_t *buf, unsigned len) {
    if (len != 32 || buf[0] != 7 || buf[1] != 1 || buf[2] > 1 || buf[3]) {
        return -EINVAL;
    }
    for (unsigned i = 11; i < len; i++) { if (buf[i]) { return -EINVAL; } }
    struct cleave_trackpad_config c = decode_config(buf + 4);
    if (cleave_trackpad_validate(&c)) { return -EINVAL; }
    /* A save is accepted only after the peripheral confirmed this sensitivity. */
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    bool confirmed = peer_sensitivity == c.sensitivity && !peer_error &&
                     peer_updated && k_uptime_get() - peer_updated < 5000;
    k_spin_unlock(&cfg_lock, key);
    if (buf[2] && !confirmed) { return -EAGAIN; }
    if (atomic_get(&save_pending)) { return -EBUSY; }
    key = k_spin_lock(&cfg_lock);
    config = c;
    generation++;
    save_error = 0;
    if (buf[2]) { save_snapshot = c; atomic_set(&save_pending, 1); }
    k_spin_unlock(&cfg_lock, key);
    if (buf[2]) { k_work_submit(&save_work); }
    return 0;
}
void cleave_trackpad_report(uint8_t *out) {
    memset(out, 0, 32);
    out[0] = 7; out[1] = 1;
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    bool fresh = peer_updated && k_uptime_get() - peer_updated < 5000;
    out[2] = (!equal_config(&config, &saved) ? 1 : 0) |
             (fresh && !peer_error && peer_sensitivity == config.sensitivity ? 2 : 0) |
             (atomic_get(&save_pending) ? 4 : 0);
    encode_config(out + 4, &config);
    out[11] = fresh ? peer_sensitivity : 0;
    out[12] = fresh ? peer_error : -ENOTCONN;
    out[13] = save_error;
    sys_put_le16(generation, out + 14);
    k_spin_unlock(&cfg_lock, key);
    out[16] = 1;
    out[17] = atomic_get(&transport_stage);
    out[18] = atomic_get(&transport_security);
    out[19] = atomic_get(&transport_att_error);
    sys_put_le16((int16_t)atomic_get(&transport_submit_error), out + 20);
    out[22] = atomic_get(&transport_length);
    sys_put_le16(atomic_get(&transport_attempts), out + 24);
    sys_put_le16(atomic_get(&transport_completions), out + 26);
}
#else
/* The driver serializes changes with packet reads on the system work queue. */
void cleave_pinnacle_sensitivity_request(uint8_t sensitivity);
uint8_t cleave_pinnacle_sensitivity_applied(void);
int8_t cleave_pinnacle_sensitivity_error(void);
int cleave_trackpad_command(const uint8_t *data, unsigned len) { return -ENOTSUP; }
void cleave_trackpad_report(uint8_t *out) { memset(out, 0, 32); }
#endif

/* Left returns desired sensitivity; right returns applied sensitivity and status.
 * Reads require the existing encrypted split connection, never a new host pairing. */
static ssize_t read_value(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                           void *buf, uint16_t len, uint16_t offset) {
    uint8_t value[3] = {1};
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    struct cleave_trackpad_config c;
    cleave_trackpad_get(&c, NULL);
    value[1] = c.sensitivity;
#else
    value[1] = cleave_pinnacle_sensitivity_applied();
    value[2] = cleave_pinnacle_sensitivity_error();
#endif
    return bt_gatt_attr_read(conn, attr, buf, len, offset, value, sizeof(value));
}
BT_GATT_SERVICE_DEFINE(cleave_trackpad_service,
    BT_GATT_PRIMARY_SERVICE(BT_UUID_DECLARE_128(TP_SERVICE)),
    BT_GATT_CHARACTERISTIC(&value_uuid.uuid, BT_GATT_CHRC_READ,
                            BT_GATT_PERM_READ_ENCRYPT, read_value, NULL, NULL));
static atomic_t read_pending;
static struct bt_gatt_read_params read_params;
static uint8_t read_done(struct bt_conn *conn, uint8_t err,
                         struct bt_gatt_read_params *params, const void *data, uint16_t len) {
    ARG_UNUSED(conn); ARG_UNUSED(params);
    atomic_inc(&transport_completions);
    atomic_set(&transport_att_error, err);
    atomic_set(&transport_length, len);
    atomic_set(&transport_stage, err ? 4 : 5);
    if (!err && data && len == 3 && ((const uint8_t *)data)[0] == 1) {
        atomic_set(&transport_stage, 6);
        const uint8_t *v = data;
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
        k_spinlock_key_t key = k_spin_lock(&cfg_lock);
        peer_sensitivity = v[1]; peer_error = (int8_t)v[2];
        peer_updated = k_uptime_get();
        k_spin_unlock(&cfg_lock, key);
#else
        if (v[1] >= 1 && v[1] <= 4) { cleave_pinnacle_sensitivity_request(v[1]); }
#endif
    }
    atomic_clear(&read_pending);
    return BT_GATT_ITER_STOP;
}
static void poll_peer(struct bt_conn *conn, void *user) {
    ARG_UNUSED(user);
    struct bt_conn_info info;
    if (bt_conn_get_info(conn, &info) || info.state != BT_CONN_STATE_CONNECTED ||
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
        info.role != BT_CONN_ROLE_CENTRAL ||
#else
        info.role != BT_CONN_ROLE_PERIPHERAL ||
#endif
        false) {
        return;
    }
    bt_security_t security = bt_conn_get_security(conn);
    atomic_set(&transport_security, security);
    if (security < BT_SECURITY_L2) { atomic_set(&transport_stage, 1); return; }
    if (!atomic_cas(&read_pending, 0, 1)) { return; }
    atomic_inc(&transport_attempts);
    atomic_set(&transport_stage, 2);
    read_params = (struct bt_gatt_read_params){.func = read_done, .handle_count = 0,
        .by_uuid = {.start_handle = 1, .end_handle = 0xffff, .uuid = &value_uuid.uuid}};
    int err = bt_gatt_read(conn, &read_params);
    atomic_set(&transport_submit_error, err);
    if (err) { atomic_set(&transport_stage, 3); atomic_clear(&read_pending); }
    else { atomic_cas(&transport_stage, 2, 7); }
}
static void poll(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(poll_work, poll);
static void poll(struct k_work *work) {
    ARG_UNUSED(work);
    bt_conn_foreach(BT_CONN_TYPE_LE, poll_peer, NULL);
    k_work_reschedule_for_queue(&cleave_peer_work_q, &poll_work, K_SECONDS(1));
}
static int trackpad_init(void) {
    k_work_schedule_for_queue(&cleave_peer_work_q, &poll_work, K_SECONDS(2));
    return 0;
}
SYS_INIT(trackpad_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
