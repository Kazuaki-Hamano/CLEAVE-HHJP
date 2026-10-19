/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zephyr/logging/log.h>
#include <zmk/ble.h>
#include <zmk/workqueue.h>
#include <zmk/studio/core.h>
#include <zmk/studio/custom.h>
#include <zmk/events/activity_settings_changed.h>
#include <cleave_split_status.h>
#include <cleave_activity_sync.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);
BUILD_ASSERT(ZMK_SPLIT_BLE_PERIPHERAL_COUNT == 1,
             "CLEAVE activity sync currently supports one peripheral");
#define SYNC_KEY "cleave_sync/activity"
#define SYNC_VERSION 1u
struct sync_record {
    uint32_t version, sequence, idle_ms, sleep_ms, pending;
};
static struct sync_record state = {.version = SYNC_VERSION};
static bool local_saved, startup_barrier_done;
K_MUTEX_DEFINE(sync_lock);
static void sync_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(sync_work, sync_work_handler);
static void schedule_sync(void) {
    k_work_reschedule_for_queue(zmk_workqueue_lowprio_work_q(), &sync_work, K_SECONDS(5));
}
static int persist(const struct sync_record *record) {
    return settings_save_one(SYNC_KEY, record, sizeof(*record));
}
int cleave_activity_sync_queue(uint32_t idle_ms, uint32_t sleep_ms) {
    k_mutex_lock(&sync_lock, K_FOREVER);
    if (state.sequence == UINT32_MAX) {
        k_mutex_unlock(&sync_lock); return -EOVERFLOW;
    }
    struct sync_record next = {SYNC_VERSION, state.sequence + 1, idle_ms, sleep_ms, 1};
    int ret = persist(&next);
    if (ret == 0) {
        state = next;
        ret = cleave_activity_store(idle_ms, sleep_ms);
        local_saved = ret == 0;
        schedule_sync();
    }
    k_mutex_unlock(&sync_lock);
    return ret;
}
void cleave_activity_sync_ack(uint8_t source, uint32_t transaction_id,
                              uint32_t idle_ms, uint32_t sleep_ms) {
    k_mutex_lock(&sync_lock, K_FOREVER);
    if (state.pending && source == 1 && transaction_id == state.sequence &&
        idle_ms == state.idle_ms && sleep_ms == state.sleep_ms) {
        struct sync_record done = state;
        done.pending = 0;
        if (persist(&done) == 0) {
            state = done;
            k_work_cancel_delayable(&sync_work);
            LOG_INF("Activity sync saved on both halves: transaction %u", transaction_id);
        }
    }
    k_mutex_unlock(&sync_lock);
}
/* settings_load() holds the settings mutex through all commits. Acquiring it
 * here via the public direct-load API waits until every boot-time h_set/commit
 * completes, preventing an old activity/s load from undoing our queued values. */
static int startup_barrier(const char *key, size_t len, settings_read_cb cb,
                           void *cb_arg, void *param) {
    return 0;
}
static void sync_work_handler(struct k_work *work) {
    if (!startup_barrier_done) {
        if (settings_load_subtree_direct("cleave_sync", startup_barrier, NULL) < 0) {
            schedule_sync(); return;
        }
        startup_barrier_done = true;
    }
    k_mutex_lock(&sync_lock, K_FOREVER);
    if (!state.pending) { k_mutex_unlock(&sync_lock); return; }
    if (!local_saved) {
        local_saved = cleave_activity_store(state.idle_ms, state.sleep_ms) == 0;
    }
    if (local_saved && cleave_split_peripheral_connected()) {
        struct zmk_activity_settings_changed event = {
            .transaction_id = state.sequence,
            .idle_ms = state.idle_ms,
            .sleep_ms = state.sleep_ms,
            .source = ZMK_RELAY_EVENT_SOURCE_SELF,
        };
        raise_zmk_activity_settings_changed(event);
    }
    /* Only an outstanding transaction runs work. No input/activity event is
     * emitted, no disconnected peer is contacted, and nothing wakes the right. */
    if (state.pending) { schedule_sync(); }
    k_mutex_unlock(&sync_lock);
}
static int sync_load(const char *name, size_t len, settings_read_cb cb, void *arg) {
    if (strcmp(name, "activity") != 0) { return -ENOENT; }
    struct sync_record loaded;
    if (len != sizeof(loaded)) { return -EINVAL; }
    int ret = cb(arg, &loaded, sizeof(loaded));
    if (ret != sizeof(loaded)) { return ret < 0 ? ret : -EINVAL; }
    if (loaded.version != SYNC_VERSION || loaded.pending > 1 ||
        (loaded.pending && loaded.sequence == 0)) { return -EINVAL; }
    state = loaded;
    local_saved = false;
    return 0;
}
static int sync_commit(void) {
    if (state.pending) { schedule_sync(); }
    return 0;
}
SETTINGS_STATIC_HANDLER_DEFINE(cleave_sync, "cleave_sync", NULL, sync_load, sync_commit, NULL);
static int sync_reset(void) {
    k_mutex_lock(&sync_lock, K_FOREVER);
    struct sync_record done = state;
    done.pending = 0;
    int ret = persist(&done);
    if (ret == 0) {
        state = done;
        k_work_cancel_delayable(&sync_work);
    }
    k_mutex_unlock(&sync_lock);
    return ret;
}
ZMK_RPC_SUBSYSTEM_SETTINGS_RESET(cleave_activity_sync, sync_reset);
