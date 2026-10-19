"""Compile production discovery callbacks with a deterministic work-queue mock."""
from pathlib import Path
import re
import subprocess

source = Path("src/studio_ble_discovery.c").read_text()
source = re.sub(r"^#include.*$", "", source, flags=re.M)
source = source[:source.index("static const struct behavior_driver_api")]
stub = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define LOG_MODULE_DECLARE(...)
#define LOG_WRN(...)
#define K_SECONDS(n) ((n)*1000)
#define ZMK_BEHAVIOR_OPAQUE 0
struct k_work {void (*handler)(struct k_work *);};
struct k_work_delayable {struct k_work work;int delay;bool active;};
#define K_WORK_DEFINE(name,fn) static struct k_work name={fn}
#define K_WORK_DELAYABLE_DEFINE(name,fn) static struct k_work_delayable name={{fn},0,false}
struct zmk_behavior_binding {int unused;};
struct zmk_behavior_binding_event {int unused;};
static struct k_work *queued;
static int starts,stops,unlocks,start_error,reschedules;
static bool advertising;
static int k_work_submit(struct k_work *w) {queued=w;return 0;}
static int k_work_reschedule(struct k_work_delayable *w,int delay) {
 w->delay=delay;w->active=true;reschedules++;return 0;
}
static int k_work_cancel_delayable(struct k_work_delayable *w) {w->active=false;return 0;}
static void zmk_studio_core_unlock(void) {unlocks++;}
static int zmk_ble_set_directed_advertising(bool enabled) {
 advertising=enabled;if(enabled){starts++;return start_error;}stops++;return 0;
}
"""
test = r"""
static void press(void) {
 assert(discovery_pressed(NULL,(struct zmk_behavior_binding_event){0})==0);
 assert(queued);queued->handler(queued);queued=NULL;
}
int main(void) {
 assert(!advertising && starts==0); /* No boot-time advertising window. */
 press();assert(advertising && starts==1 && unlocks==1);
 assert(discovery_timeout.active && discovery_timeout.delay==60000);
 assert(discovery_released(NULL,(struct zmk_behavior_binding_event){0})==0);
 assert(stops==0);
 press();assert(starts==2 && reschedules==2); /* Repeated press renews window. */
 discovery_timeout.work.handler(&discovery_timeout.work);
 assert(!advertising && stops==1); /* Only advertising API is called. */
 press();assert(advertising);
 start_error=-1;press();
 assert(!advertising && !discovery_timeout.active); /* Failure clears enable flag. */
 puts("BLE discovery manual start / 60-second renewal / expiry / failure: PASS");
}
"""
subprocess.run(
    ["wsl", "--", "bash", "-lc",
     "gcc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -x c -o /tmp/cleave-ble-discovery - && /tmp/cleave-ble-discovery"],
    input=(stub + source + test).encode(), check=True,
)
