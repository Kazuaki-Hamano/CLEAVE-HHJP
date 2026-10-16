/* SPDX-License-Identifier: MIT */
#define DT_DRV_COMPAT cleave_behavior_trackpad_settings
#include <string.h>
#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/input/input.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/event_manager.h>
#include <zmk/events/split_peripheral_status_changed.h>
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
#include <zmk/split/central.h>
#else
#include <zmk/split/peripheral.h>
#endif
#include "trackpad_settings.h"
#include "trackpad_status.h"
#include "trackpad_math.h"

#define TP_SERVICE BT_UUID_128_ENCODE(0xb6f4a630, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10)
#define TP_VALUE BT_UUID_128_ENCODE(0xb6f4a631, 0x3790, 0x4c3c, 0x934d, 0x911d84233b10)
static struct bt_uuid_128 value_uuid = BT_UUID_INIT_128(TP_VALUE);
static struct k_spinlock cfg_lock;
static struct cleave_trackpad_config config = {200, 0, 300, 1, 100};
static uint32_t generation = 1;
/* Diagnostic fields are exported in previously reserved bytes of Report 7. */
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static atomic_t transport_stage;
static atomic_t transport_security;
static atomic_t transport_submit_error;
static atomic_t transport_att_error;
static atomic_t transport_length;
static atomic_t transport_attempts;
static atomic_t transport_completions;
static struct cleave_trackpad_config saved = {200, 0, 300, 1, 100};
static uint8_t peer_sensitivity;
static int8_t peer_error;
static int64_t peer_updated;
static atomic_t save_pending;
static int8_t save_error;
#endif

int cleave_trackpad_validate(const struct cleave_trackpad_config *c) {
    return c->speed >= 30 && c->speed <= 800 && c->speed % 10 == 0 && c->acceleration <= 300 &&
           c->maximum >= 100 && c->maximum <= 800 &&
           c->maximum % 10 == 0 && c->sensitivity == 1 &&
           c->scroll >= 10 && c->scroll <= 400 && c->scroll % 10 == 0 ? 0 : -EINVAL;
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
           a->maximum == b->maximum && a->sensitivity == b->sensitivity &&
           a->scroll == b->scroll;
}
static void encode_config(uint8_t *buf, const struct cleave_trackpad_config *c) {
    sys_put_le16(c->speed, buf);
    sys_put_le16(c->acceleration, buf + 2);
    sys_put_le16(c->maximum, buf + 4);
    buf[6] = 1;
    sys_put_le16(c->scroll, buf + 7);
}
static struct cleave_trackpad_config decode_config(const uint8_t *buf) {
    return (struct cleave_trackpad_config){sys_get_le16(buf), sys_get_le16(buf + 2),
                                         sys_get_le16(buf + 4), buf[6], sys_get_le16(buf + 7)};
}
static int settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    if (strcmp(name, "config")) { return -ENOENT; }
    uint8_t buf[10] = {0};
    if (len != 8 && len != sizeof(buf)) { return -EINVAL; }
    int n = read_cb(cb_arg, buf, len);
    if (n < 0 || (size_t)n != len || (len == 8 ? buf[0] != 1 : buf[0] != 2)) { return -EINVAL; }
    if (len == 8) {
        /* Migrate saved cursor tuning; sensitivity is now always 1x. */
        buf[7] = 1;
        sys_put_le16(100, buf + 8);
        uint16_t speed = sys_get_le16(buf + 1);
        uint16_t maximum = sys_get_le16(buf + 5);
        if (speed < 25 || speed > 800 || maximum < 100 || maximum > 800) { return -EINVAL; }
        sys_put_le16(trackpad_snap_multiplier(speed), buf + 1);
        sys_put_le16(trackpad_snap_multiplier(maximum), buf + 5);
    }
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
    uint8_t buf[10] = {2};
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
    if (len != 32 || buf[0] != 7 || buf[1] != 2 || buf[2] > 1 || buf[3]) {
        return -EINVAL;
    }
    for (unsigned i = 11; i < len; i++) {
        if (i != 28 && i != 29 && buf[i]) { return -EINVAL; }
    }
    uint8_t packed[9];
    memcpy(packed, buf + 4, 7);
    memcpy(packed + 7, buf + 28, 2);
    struct cleave_trackpad_config c = decode_config(packed);
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
    out[0] = 7; out[1] = 2;
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    bool fresh = peer_updated && k_uptime_get() - peer_updated < 5000;
    out[2] = (!equal_config(&config, &saved) ? 1 : 0) |
             (fresh && !peer_error && peer_sensitivity == config.sensitivity ? 2 : 0) |
             (atomic_get(&save_pending) ? 4 : 0);
    uint8_t packed[9];
    encode_config(packed, &config);
    memcpy(out + 4, packed, 7);
    memcpy(out + 28, packed + 7, 2);
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

/* Retain the legacy encrypted read service for older diagnostic tooling.
 * Runtime tuning now uses the standard split behavior/input transport below. */
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

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
static void receive_status(struct input_event *event) {
    if (event->dev != DEVICE_DT_GET(DT_NODELABEL(trackpad_split)) ||
        event->type != INPUT_EV_MSC || event->code != CLEAVE_TRACKPAD_STATUS_CODE) { return; }
    uint8_t applied;
    int8_t error;
    if (!cleave_trackpad_status_decode(event->value, &applied, &error)) { return; }
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    peer_sensitivity = applied;
    peer_error = error;
    peer_updated = k_uptime_get();
    k_spin_unlock(&cfg_lock, key);
    atomic_inc(&transport_completions);
    atomic_set(&transport_length, 4);
    atomic_set(&transport_stage, 9);
}
INPUT_CALLBACK_DEFINE(DEVICE_DT_GET(DT_NODELABEL(trackpad_split)), receive_status);

static int split_status(const zmk_event_t *event) {
    const struct zmk_split_peripheral_status_changed *status =
        as_zmk_split_peripheral_status_changed(event);
    if (status && !status->connected) {
        k_spinlock_key_t key = k_spin_lock(&cfg_lock);
        peer_updated = 0;
        k_spin_unlock(&cfg_lock, key);
        atomic_set(&transport_stage, 0);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(cleave_trackpad_split_status, split_status);
ZMK_SUBSCRIPTION(cleave_trackpad_split_status, zmk_split_peripheral_status_changed);

static void poll(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(poll_work, poll);
static void poll(struct k_work *work) {
    ARG_UNUSED(work);
    struct cleave_trackpad_config cfg;
    cleave_trackpad_get(&cfg, NULL);
    struct zmk_behavior_binding binding = {
        .behavior_dev = DEVICE_DT_NAME(DT_NODELABEL(tp_sens)), .param1 = cfg.sensitivity};
    struct zmk_behavior_binding_event event = {.source = 0, .position = 0,
                                               .timestamp = k_uptime_get()};
    atomic_inc(&transport_attempts);
    int err = zmk_split_central_invoke_behavior(0, &binding, event, true);
    atomic_set(&transport_submit_error, err);
    /* Keep the successful response stage visible until its freshness expires. */
    k_spinlock_key_t key = k_spin_lock(&cfg_lock);
    bool fresh = peer_updated && k_uptime_get() - peer_updated < 5000;
    k_spin_unlock(&cfg_lock, key);
    if (!fresh) { atomic_set(&transport_stage, err ? 3 : 8); }
    k_work_reschedule(&poll_work, K_SECONDS(1));
}
static int trackpad_init(void) {
    k_work_schedule(&poll_work, K_SECONDS(2));
    return 0;
}
SYS_INIT(trackpad_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
#else
static void send_status(struct k_work *work) {
    ARG_UNUSED(work);
    struct zmk_split_transport_peripheral_event event = {
        .type = ZMK_SPLIT_TRANSPORT_PERIPHERAL_EVENT_TYPE_INPUT_EVENT,
        .data = {.input_event = {.reg = 0, .type = INPUT_EV_MSC,
            .code = CLEAVE_TRACKPAD_STATUS_CODE, .sync = false,
            .value = cleave_trackpad_status_encode(cleave_pinnacle_sensitivity_applied(),
                                                   cleave_pinnacle_sensitivity_error())}}};
    zmk_split_peripheral_report_event(&event);
}
K_WORK_DELAYABLE_DEFINE(status_work, send_status);
#endif

static int request_sensitivity(struct zmk_behavior_binding *binding,
                                struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
    if (binding->param1 != 1) { return -EINVAL; }
#if !IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    cleave_pinnacle_sensitivity_request(binding->param1);
    /* Sensor work and this response run serially on the system work queue. */
    k_work_reschedule(&status_work, K_MSEC(50));
#endif
    return ZMK_BEHAVIOR_OPAQUE;
}
static const struct behavior_driver_api sensitivity_api = {
    .binding_pressed = request_sensitivity, .locality = BEHAVIOR_LOCALITY_EVENT_SOURCE,
};
BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &sensitivity_api);
