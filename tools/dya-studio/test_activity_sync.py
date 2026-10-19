"""Exercise production queue/store/peripheral apply code with deterministic flash/transport mocks."""
from pathlib import Path
import re
import subprocess
base=Path("modules/settings-rpc")
def strip(path):
 return re.sub(r"^#include .*$","",path.read_text(),flags=re.M)
headers=strip(base/"include/zmk/events/activity_settings_changed.h")+strip(base/"include/zmk/events/activity_settings_report.h")
headers=re.sub(r"^#pragma once$","",headers,flags=re.M)
source=strip(base/"src/activity_store.c")+strip(base/"src/activity_sync.c")+strip(base/"src/events/activity_settings_changed.c")
stub=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define ZMK_EVENT_DECLARE(...)
#define ZMK_EVENT_IMPL(...)
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
#define ZMK_RELAY_EVENT_HANDLE(...)
#define ZMK_RPC_SUBSYSTEM_SETTINGS_RESET(...)
#define ZMK_RELAY_EVENT_SOURCE_SELF 255
#define ZMK_EV_EVENT_BUBBLE 0
#define CONFIG_ZMK_SPLIT_RELAY_EVENT 1
#define IS_ENABLED(x) (x)
#define LOG_MODULE_DECLARE(...)
#define LOG_INF(...)
#define LOG_DBG(...)
#define LOG_WRN(...)
#define BUILD_ASSERT(cond,msg) _Static_assert(cond,msg)
#define ZMK_SPLIT_BLE_PERIPHERAL_COUNT 1
#define K_FOREVER 0
#define K_SECONDS(n) (n)
struct k_work {int unused;};
struct delay_work {int unused;};
#define K_WORK_DELAYABLE_DEFINE(name,handler) struct delay_work name
#define K_MUTEX_DEFINE(name) int name
#define SETTINGS_STATIC_HANDLER_DEFINE(...)
static int scheduled,canceled;
static void k_mutex_lock(int *p,int t) {}
static void k_mutex_unlock(int *p) {}
static void *zmk_workqueue_lowprio_work_q(void) {return NULL;}
static int k_work_reschedule_for_queue(void *q,struct delay_work *w,int t) {assert(t==5);scheduled++;return 0;}
static int k_work_cancel_delayable(struct delay_work *w) {canceled++;return 0;}
typedef int (*settings_read_cb)(void *,void *,size_t);
static int side,flash_fail_side=-1,outbox_fail;
static unsigned char disk[20];static bool disk_present,connected;
static uint32_t idle[2]={30000,30000},sleep_ms[2]={1800000,1800000},saved_idle[2],saved_sleep[2];
static int idle_writes,sleep_writes;
static uint32_t zmk_activity_get_idle_ms(void) {return idle[side];}
static uint32_t zmk_activity_get_sleep_ms(void) {return sleep_ms[side];}
static bool zmk_activity_set_idle_ms(uint32_t v) {idle[side]=v;idle_writes++;return true;}
static bool zmk_activity_set_sleep_ms(uint32_t v) {sleep_ms[side]=v;sleep_writes++;return true;}
static bool cleave_split_peripheral_connected(void) {return connected;}
static int settings_save_one(const char *key,const void *p,size_t n) {
 if(strcmp(key,"cleave_sync/activity")==0) {
  assert(n==20);if(outbox_fail)return -EIO;memcpy(disk,p,n);disk_present=true;return 0;
 }
 assert(strcmp(key,"activity/s")==0 && n==8);
 if(side==flash_fail_side)return -EIO;
 const uint32_t *v=p;saved_sleep[side]=v[0];saved_idle[side]=v[1];return 0;
}
static int settings_load_subtree_direct(const char *key,int (*cb)(const char *,size_t,settings_read_cb,void *,void *),void *param) {return 0;}
"""
bridge=r"""
typedef struct zmk_activity_settings_changed zmk_event_t;
static struct zmk_activity_settings_changed last_change;
static struct zmk_activity_settings_report last_report;
static int sent,reports;
static struct zmk_activity_settings_changed *as_zmk_activity_settings_changed(const zmk_event_t *p) {return (void *)p;}
static int raise_zmk_activity_settings_changed(struct zmk_activity_settings_changed ev) {last_change=ev;sent++;return 0;}
static int raise_zmk_activity_settings_report(struct zmk_activity_settings_report ev) {last_report=ev;reports++;return 0;}
"""
test=r"""
static int disk_read(void *arg,void *out,size_t n) {memcpy(out,disk,n);return n;}
static void reboot(void) {
 state=(struct sync_record){.version=SYNC_VERSION};local_saved=false;startup_barrier_done=false;
 assert(sync_load("activity",sizeof(disk),disk_read,NULL)==0);sync_commit();
}
static void deliver(void) {
 side=1;last_change.source=0;activity_settings_changed_listener(&last_change);side=0;
}
static void ack(void) {cleave_activity_sync_ack(1,last_report.transaction_id,last_report.idle_ms,last_report.sleep_ms);}
int main(void) {
 /* No queued change must leave independently loaded values alone. */
 idle[1]=70000;sync_commit();sync_work_handler(NULL);assert(sent==0 && idle[1]==70000);
 outbox_fail=1;assert(cleave_activity_sync_queue(40000,600000)==-EIO);assert(!state.pending && !disk_present);
 outbox_fail=0;assert(cleave_activity_sync_queue(40000,600000)==0);assert(state.pending && saved_idle[0]==40000 && saved_sleep[0]==600000);
 sync_work_handler(NULL);assert(sent==0 && state.pending); /* Offline: no relay or wake. */
 uint32_t first=state.sequence;
 assert(cleave_activity_sync_queue(45000,900000)==0);assert(state.sequence==first+1);
 cleave_activity_sync_ack(1,first,40000,600000);assert(state.pending);
 reboot();assert(state.pending && state.idle_ms==45000); /* Persisted pending survives central restart. */
 connected=true;sync_work_handler(NULL);assert(sent==1 && last_change.idle_ms==45000 && last_change.transaction_id==state.sequence);
 flash_fail_side=1;deliver();assert(reports==0 && state.pending); /* No ack before durable right save. */
 flash_fail_side=-1;sync_work_handler(NULL);deliver();assert(reports==1 && saved_idle[1]==45000 && saved_sleep[1]==900000);
 cleave_activity_sync_ack(0,last_report.transaction_id,45000,900000);assert(state.pending);
 cleave_activity_sync_ack(1,last_report.transaction_id,45001,900000);assert(state.pending);
 outbox_fail=1;ack();assert(state.pending);outbox_fail=0;ack();assert(!state.pending && canceled>0);
 int before=sent;sync_work_handler(NULL);assert(sent==before); /* No work/relay after ack. */
 reboot();assert(!state.pending);sync_work_handler(NULL);assert(sent==before);
 flash_fail_side=0;assert(cleave_activity_sync_queue(47000,1100000)==-EIO);assert(state.pending);
 before=sent;sync_work_handler(NULL);assert(sent==before);
 flash_fail_side=-1;sync_work_handler(NULL);assert(sent==before+1);deliver();ack();assert(!state.pending);
 uint32_t sequence=state.sequence;
 assert(cleave_activity_sync_queue(60000,1200000)==0);assert(state.sequence==sequence+1);
 outbox_fail=1;assert(sync_reset()==-EIO && state.pending);outbox_fail=0;
 assert(sync_reset()==0 && !state.pending);reboot();assert(!state.pending);ack();assert(!state.pending);
 /* Duplicate delivery saves again but avoids activity setter churn. */
 int iw=idle_writes,sw=sleep_writes;deliver();assert(idle_writes==iw && sleep_writes==sw);
 assert(sync_load("bad",20,disk_read,NULL)==-ENOENT);
 assert(sync_load("activity",19,disk_read,NULL)==-EINVAL);
 idle[1]=71000;reboot();sync_work_handler(NULL);assert(idle[1]==71000 && !state.pending);
 state.sequence=UINT32_MAX;assert(cleave_activity_sync_queue(1,2)==-EOVERFLOW);
 uint32_t bad_version=99;memcpy(disk,&bad_version,4);assert(sync_load("activity",20,disk_read,NULL)==-EINVAL);
 puts("Durable outbox, coalescing, offline retry, reboot, saved ack, stale ack, reset and no-op tests: PASS");
}
"""
command="gcc -std=c11 -Wall -Wextra -Werror -Wno-unused-function -Wno-unused-variable -Wno-unused-parameter -Wno-sign-compare -x c -o /tmp/cleave-activity-sync - && /tmp/cleave-activity-sync"
subprocess.run(["wsl","--","bash","-lc",command],input=(stub+headers+bridge+source+test).encode(),check=True)
